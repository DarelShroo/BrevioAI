"""Mongo repositories for UsageRecord / CostRecord (FASE 4)."""

from __future__ import annotations

from typing import List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from core.brevio_api.models.billing.usage_models import CostRecord, UsageRecord


class UsageRecordRepository:
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self.collection = collection

    async def ensure_indexes(self) -> None:
        await self.collection.create_index(
            [("job_id", 1), ("attempt_id", 1)],
            unique=True,
            name="usage_job_attempt_unique",
        )
        await self.collection.create_index([("job_id", 1)], name="usage_job")
        await self.collection.create_index(
            [("user_id", 1), ("created_at", 1)], name="usage_user_created"
        )

    async def create(self, record: UsageRecord) -> UsageRecord:
        payload = record.model_dump(by_alias=True)
        payload["_id"] = ObjectId(payload["_id"])
        payload["user_id"] = ObjectId(str(payload["user_id"]))
        try:
            await self.collection.insert_one(payload)
            return record
        except DuplicateKeyError:
            existing = await self.get_by_attempt(record.job_id, record.attempt_id)
            if existing:
                return existing
            raise

    async def get_by_attempt(
        self, job_id: str, attempt_id: str
    ) -> Optional[UsageRecord]:
        doc = await self.collection.find_one(
            {"job_id": job_id, "attempt_id": attempt_id}
        )
        if not doc:
            return None
        payload = dict(doc)
        payload["id"] = payload.pop("_id")
        return UsageRecord.model_validate(payload)

    async def list_by_job(self, job_id: str) -> List[UsageRecord]:
        cursor = self.collection.find({"job_id": job_id}).sort("created_at", 1)
        rows = await cursor.to_list(length=10_000)
        out: List[UsageRecord] = []
        for doc in rows:
            payload = dict(doc)
            payload["id"] = payload.pop("_id")
            out.append(UsageRecord.model_validate(payload))
        return out


class CostRecordRepository:
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self.collection = collection

    async def ensure_indexes(self) -> None:
        await self.collection.create_index(
            [("usage_id", 1)], unique=True, name="cost_usage_unique"
        )
        await self.collection.create_index([("job_id", 1)], name="cost_job")

    async def create(self, record: CostRecord) -> CostRecord:
        payload = record.model_dump(by_alias=True)
        payload["_id"] = ObjectId(payload["_id"])
        payload["usage_id"] = ObjectId(str(payload["usage_id"]))
        payload["user_id"] = ObjectId(str(payload["user_id"]))
        try:
            await self.collection.insert_one(payload)
            return record
        except DuplicateKeyError:
            existing = await self.get_by_usage_id(str(record.usage_id))
            if existing:
                return existing
            raise

    async def get_by_usage_id(self, usage_id: str) -> Optional[CostRecord]:
        doc = await self.collection.find_one({"usage_id": ObjectId(usage_id)})
        if not doc:
            return None
        payload = dict(doc)
        payload["id"] = payload.pop("_id")
        return CostRecord.model_validate(payload)

    async def list_by_job(self, job_id: str) -> List[CostRecord]:
        cursor = self.collection.find({"job_id": job_id}).sort("created_at", 1)
        rows = await cursor.to_list(length=10_000)
        out: List[CostRecord] = []
        for doc in rows:
            payload = dict(doc)
            payload["id"] = payload.pop("_id")
            out.append(CostRecord.model_validate(payload))
        return out


def usage_billing_collections(
    db: AsyncIOMotorDatabase,
) -> dict[str, AsyncIOMotorCollection]:
    return {
        "usage": db.get_collection("usage_records"),
        "costs": db.get_collection("cost_records"),
    }
