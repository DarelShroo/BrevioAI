"""Mongo repos for product period usage and per-job product records."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from core.brevio_api.models.billing.plan_models import (
    ProductPeriodUsage,
    ProductUsageRecord,
    utcnow,
)


class ProductPeriodUsageRepository:
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self.collection = collection

    async def ensure_indexes(self) -> None:
        await self.collection.create_index(
            [("user_id", 1), ("period_start", 1), ("period_end", 1)],
            unique=True,
            name="product_period_user_unique",
        )

    async def get_period(
        self, user_id: str, period_start: datetime, period_end: datetime
    ) -> Optional[ProductPeriodUsage]:
        doc = await self.collection.find_one(
            {
                "user_id": ObjectId(user_id),
                "period_start": period_start,
                "period_end": period_end,
            }
        )
        if not doc:
            return None
        payload = dict(doc)
        payload["id"] = payload.pop("_id")
        return ProductPeriodUsage.model_validate(payload)

    async def create(self, usage: ProductPeriodUsage) -> ProductPeriodUsage:
        payload = usage.model_dump(by_alias=True)
        payload["_id"] = ObjectId(payload["_id"])
        payload["user_id"] = ObjectId(str(payload["user_id"]))
        try:
            await self.collection.insert_one(payload)
            return usage
        except DuplicateKeyError:
            existing = await self.get_period(
                str(usage.user_id), usage.period_start, usage.period_end
            )
            if existing:
                return existing
            raise

    async def atomic_reserve(
        self,
        *,
        user_id: str,
        period_start: datetime,
        period_end: datetime,
        plan_id: str,
        plan_version: str,
        documents: int,
        pages: int,
        bytes_amount: int,
        documents_limit: int,
        pages_limit: int,
        bytes_limit: int,
        concurrent_limit: int,
        credits_hold: int = 0,
        credits_limit: int = 10**9,
    ) -> Optional[ProductPeriodUsage]:
        """Atomically increment usage if remaining capacity is enough.

        ``credits_hold`` (FASE 6): coarse period-credit gate incremented at admit
        together with documents/pages so concurrent admits cannot race past
        ``credits_per_period``. Hold is released on product release; settlement
        moves hold → ``credits_used``.
        """
        docs = max(0, int(documents))
        pgs = max(0, int(pages))
        byts = max(0, int(bytes_amount))
        hold = max(0, int(credits_hold))
        # Ensure document exists first.
        await self.create(
            ProductPeriodUsage(
                user_id=ObjectId(user_id),
                plan_id=plan_id,
                plan_version=plan_version,
                period_start=period_start,
                period_end=period_end,
            )
        )
        filt: dict = {
            "user_id": ObjectId(user_id),
            "period_start": period_start,
            "period_end": period_end,
            "documents_used": {"$lte": documents_limit - docs},
            "pages_used": {"$lte": pages_limit - pgs},
            "bytes_used": {"$lte": bytes_limit - byts},
            "concurrent_jobs": {"$lt": concurrent_limit},
        }
        inc: dict = {
            "documents_used": docs,
            "pages_used": pgs,
            "bytes_used": byts,
            "concurrent_jobs": 1,
            "version": 1,
        }
        if hold > 0:
            # credits_budget tracks used+hold without $expr (mongomock-safe).
            filt["credits_budget"] = {"$lte": credits_limit - hold}
            inc["credits_hold_active"] = hold
            inc["credits_budget"] = hold
        doc = await self.collection.find_one_and_update(
            filt,
            {
                "$inc": inc,
                "$set": {
                    "updated_at": utcnow(),
                    "plan_id": plan_id,
                    "plan_version": plan_version,
                },
            },
            return_document=ReturnDocument.AFTER,
        )
        if not doc:
            return None
        payload = dict(doc)
        payload["id"] = payload.pop("_id")
        return ProductPeriodUsage.model_validate(payload)

    async def release_concurrency(self, user_id: str, period_start: datetime, period_end: datetime) -> None:
        await self.collection.update_one(
            {
                "user_id": ObjectId(user_id),
                "period_start": period_start,
                "period_end": period_end,
                "concurrent_jobs": {"$gt": 0},
            },
            {
                "$inc": {"concurrent_jobs": -1, "version": 1},
                "$set": {"updated_at": utcnow()},
            },
        )

    async def rollback_reserve(
        self,
        *,
        user_id: str,
        period_start: datetime,
        period_end: datetime,
        documents: int,
        pages: int,
        bytes_amount: int,
        release_concurrency: bool = True,
        credits_hold: int = 0,
    ) -> None:
        inc = {
            "documents_used": -max(0, documents),
            "pages_used": -max(0, pages),
            "bytes_used": -max(0, bytes_amount),
            "version": 1,
        }
        if release_concurrency:
            inc["concurrent_jobs"] = -1
        if credits_hold > 0:
            inc["credits_hold_active"] = -max(0, credits_hold)
            inc["credits_budget"] = -max(0, credits_hold)
        await self.collection.update_one(
            {
                "user_id": ObjectId(user_id),
                "period_start": period_start,
                "period_end": period_end,
            },
            {"$inc": inc, "$set": {"updated_at": utcnow()}},
        )
        # Soft clamp: if counters went negative due to races, zero them.
        current = await self.get_period(user_id, period_start, period_end)
        if current is None:
            return
        fixes = {}
        if current.documents_used < 0:
            fixes["documents_used"] = 0
        if current.pages_used < 0:
            fixes["pages_used"] = 0
        if current.bytes_used < 0:
            fixes["bytes_used"] = 0
        if current.concurrent_jobs < 0:
            fixes["concurrent_jobs"] = 0
        hold_active = getattr(current, "credits_hold_active", 0) or 0
        if hold_active < 0:
            fixes["credits_hold_active"] = 0
        budget = getattr(current, "credits_budget", 0) or 0
        if budget < 0:
            fixes["credits_budget"] = 0
        if fixes:
            await self.collection.update_one(
                {
                    "user_id": ObjectId(user_id),
                    "period_start": period_start,
                    "period_end": period_end,
                },
                {"$set": fixes},
            )

    async def release_credits_hold(
        self,
        *,
        user_id: str,
        period_start: datetime,
        period_end: datetime,
        hold: int,
    ) -> None:
        hold = max(0, int(hold))
        if hold == 0:
            return
        await self.collection.update_one(
            {
                "user_id": ObjectId(user_id),
                "period_start": period_start,
                "period_end": period_end,
                "credits_hold_active": {"$gte": hold},
            },
            {
                "$inc": {
                    "credits_hold_active": -hold,
                    "credits_budget": -hold,
                    "version": 1,
                },
                "$set": {"updated_at": utcnow()},
            },
        )

    async def atomic_add_credits(
        self,
        *,
        user_id: str,
        period_start: datetime,
        period_end: datetime,
        credits: int,
        credits_limit: int,
    ) -> Optional[ProductPeriodUsage]:
        """Increment settled credits_used; budget grows only for overshoot past hold."""
        credits = max(0, int(credits))
        if credits == 0:
            return await self.get_period(user_id, period_start, period_end)
        # Prefer staying within limit: only accept if budget + credits <= limit
        # (hold already released, so budget was reduced by hold; add consumed).
        doc = await self.collection.find_one_and_update(
            {
                "user_id": ObjectId(user_id),
                "period_start": period_start,
                "period_end": period_end,
                "credits_budget": {"$lte": credits_limit - credits},
            },
            {
                "$inc": {
                    "credits_used": credits,
                    "credits_budget": credits,
                    "version": 1,
                },
                "$set": {"updated_at": utcnow()},
            },
            return_document=ReturnDocument.AFTER,
        )
        if not doc:
            # Clamp: record used up to remaining budget room only.
            current = await self.get_period(user_id, period_start, period_end)
            if current is None:
                return None
            remaining = max(0, credits_limit - int(current.credits_budget or 0))
            apply = min(credits, remaining)
            if apply <= 0:
                # Still record credits_used for observability but do not grow budget past limit.
                doc = await self.collection.find_one_and_update(
                    {
                        "user_id": ObjectId(user_id),
                        "period_start": period_start,
                        "period_end": period_end,
                    },
                    {
                        "$inc": {"credits_used": credits, "version": 1},
                        "$set": {"updated_at": utcnow()},
                    },
                    return_document=ReturnDocument.AFTER,
                )
            else:
                doc = await self.collection.find_one_and_update(
                    {
                        "user_id": ObjectId(user_id),
                        "period_start": period_start,
                        "period_end": period_end,
                    },
                    {
                        "$inc": {
                            "credits_used": credits,
                            "credits_budget": apply,
                            "version": 1,
                        },
                        "$set": {"updated_at": utcnow()},
                    },
                    return_document=ReturnDocument.AFTER,
                )
        if not doc:
            return None
        payload = dict(doc)
        payload["id"] = payload.pop("_id")
        return ProductPeriodUsage.model_validate(payload)


class ProductUsageRecordRepository:
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self.collection = collection

    async def ensure_indexes(self) -> None:
        await self.collection.create_index(
            [("job_id", 1)], unique=True, name="product_usage_job_unique"
        )
        await self.collection.create_index(
            [("user_id", 1), ("period_start", 1)], name="product_usage_user_period"
        )

    async def get_by_job(self, job_id: str) -> Optional[ProductUsageRecord]:
        doc = await self.collection.find_one({"job_id": job_id})
        if not doc:
            return None
        payload = dict(doc)
        payload["id"] = payload.pop("_id")
        return ProductUsageRecord.model_validate(payload)

    async def create(self, record: ProductUsageRecord) -> ProductUsageRecord:
        payload = record.model_dump(by_alias=True)
        payload["_id"] = ObjectId(payload["_id"])
        payload["user_id"] = ObjectId(str(payload["user_id"]))
        try:
            await self.collection.insert_one(payload)
            return record
        except DuplicateKeyError:
            existing = await self.get_by_job(record.job_id)
            if existing:
                return existing
            raise

    async def mark_status(
        self, job_id: str, *, from_status: str, to_status: str
    ) -> Optional[ProductUsageRecord]:
        doc = await self.collection.find_one_and_update(
            {"job_id": job_id, "status": from_status},
            {"$set": {"status": to_status, "updated_at": utcnow()}},
            return_document=ReturnDocument.AFTER,
        )
        if not doc:
            return None
        payload = dict(doc)
        payload["id"] = payload.pop("_id")
        return ProductUsageRecord.model_validate(payload)


def product_billing_collections(
    db: AsyncIOMotorDatabase,
) -> dict[str, AsyncIOMotorCollection]:
    return {
        "period_usage": db.get_collection("product_period_usage"),
        "product_usage": db.get_collection("product_usage_records"),
    }
