"""Mongo repositories for credit billing (FASE 3)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from core.brevio_api.models.billing.credit_models import (
    CreditAccount,
    CreditLedgerEntry,
    CreditReservation,
    JobSettlement,
    ReservationStatus,
    SettlementStatus,
    utcnow,
)

logger = logging.getLogger(__name__)


class CreditAccountRepository:
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self.collection = collection

    async def ensure_indexes(self) -> None:
        await self.collection.create_index(
            [("user_id", 1)], unique=True, name="credit_account_user_unique"
        )

    async def get_by_user_id(self, user_id: str) -> Optional[CreditAccount]:
        doc = await self.collection.find_one({"user_id": ObjectId(user_id)})
        if not doc:
            return None
        payload = dict(doc)
        payload["id"] = payload.pop("_id")
        return CreditAccount.model_validate(payload)

    async def create(self, account: CreditAccount) -> CreditAccount:
        payload = account.model_dump(by_alias=True)
        payload["_id"] = ObjectId(payload["_id"])
        payload["user_id"] = ObjectId(str(payload["user_id"]))
        try:
            await self.collection.insert_one(payload)
        except DuplicateKeyError:
            existing = await self.get_by_user_id(str(account.user_id))
            if existing:
                return existing
            raise
        return account

    async def atomic_debit_if_available(
        self, user_id: str, amount: int
    ) -> Optional[CreditAccount]:
        """Atomically decrement balance if balance >= amount. Returns updated account."""
        if amount < 0:
            raise ValueError("debit amount must be >= 0")
        if amount == 0:
            return await self.get_by_user_id(user_id)
        doc = await self.collection.find_one_and_update(
            {"user_id": ObjectId(user_id), "balance": {"$gte": amount}},
            {
                "$inc": {"balance": -amount, "version": 1},
                "$set": {"updated_at": utcnow()},
            },
            return_document=ReturnDocument.AFTER,
        )
        if not doc:
            return None
        payload = dict(doc)
        payload["id"] = payload.pop("_id")
        return CreditAccount.model_validate(payload)

    async def atomic_credit(self, user_id: str, amount: int) -> Optional[CreditAccount]:
        if amount < 0:
            raise ValueError("credit amount must be >= 0")
        if amount == 0:
            return await self.get_by_user_id(user_id)
        doc = await self.collection.find_one_and_update(
            {"user_id": ObjectId(user_id)},
            {
                "$inc": {"balance": amount, "version": 1},
                "$set": {"updated_at": utcnow()},
            },
            return_document=ReturnDocument.AFTER,
        )
        if not doc:
            return None
        payload = dict(doc)
        payload["id"] = payload.pop("_id")
        return CreditAccount.model_validate(payload)

    async def atomic_period_grant(
        self,
        user_id: str,
        *,
        included: int,
        rollover_max: int,
        grant_key: str,
    ) -> Optional[tuple[CreditAccount, int]]:
        """Apply included credits with rollover cap. Idempotent on grant_key.

        final = min(balance + included, rollover_max)
        Returns (account, delta) when this caller won the grant; None if already applied.
        """
        if included < 0:
            raise ValueError("included credits must be >= 0")
        if rollover_max < 0:
            raise ValueError("rollover_max must be >= 0")
        oid = ObjectId(user_id)
        for _ in range(8):
            current = await self.get_by_user_id(user_id)
            if current is None:
                return None
            if current.last_period_grant_key == grant_key:
                return None
            before = int(current.balance)
            final = min(before + int(included), int(rollover_max))
            delta = final - before
            doc = await self.collection.find_one_and_update(
                {
                    "user_id": oid,
                    "version": int(current.version),
                    "$or": [
                        {"last_period_grant_key": {"$ne": grant_key}},
                        {"last_period_grant_key": {"$exists": False}},
                        {"last_period_grant_key": None},
                    ],
                },
                {
                    "$set": {
                        "balance": final,
                        "last_period_grant_key": grant_key,
                        "updated_at": utcnow(),
                    },
                    "$inc": {"version": 1},
                },
                return_document=ReturnDocument.AFTER,
            )
            if doc:
                payload = dict(doc)
                payload["id"] = payload.pop("_id")
                return CreditAccount.model_validate(payload), delta
            # Version conflict or concurrent grant — retry.
        # Lost race after retries: treat as already applied if key matches.
        again = await self.get_by_user_id(user_id)
        if again and again.last_period_grant_key == grant_key:
            return None
        raise RuntimeError(f"period grant contention user_id={user_id} key={grant_key}")


class CreditReservationRepository:
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self.collection = collection

    async def ensure_indexes(self) -> None:
        await self.collection.create_index(
            [("job_id", 1)], unique=True, name="credit_reservation_job_unique"
        )
        await self.collection.create_index(
            [("user_id", 1), ("status", 1)], name="credit_reservation_user_status"
        )
        await self.collection.create_index(
            [("expires_at", 1), ("status", 1)],
            name="credit_reservation_expires_status",
        )

    async def get_by_job_id(self, job_id: str) -> Optional[CreditReservation]:
        doc = await self.collection.find_one({"job_id": job_id})
        if not doc:
            return None
        payload = dict(doc)
        payload["id"] = payload.pop("_id")
        return CreditReservation.model_validate(payload)

    async def create(self, reservation: CreditReservation) -> CreditReservation:
        payload = reservation.model_dump(by_alias=True)
        payload["_id"] = ObjectId(payload["_id"])
        payload["user_id"] = ObjectId(str(payload["user_id"]))
        payload["account_id"] = ObjectId(str(payload["account_id"]))
        try:
            await self.collection.insert_one(payload)
            return reservation
        except DuplicateKeyError:
            existing = await self.get_by_job_id(reservation.job_id)
            if existing:
                return existing
            raise

    async def transition_status(
        self,
        reservation_id: ObjectId | str,
        *,
        from_status: str,
        to_status: str,
        extra_set: Optional[Dict[str, Any]] = None,
    ) -> Optional[CreditReservation]:
        oid = (
            reservation_id
            if isinstance(reservation_id, ObjectId)
            else ObjectId(str(reservation_id))
        )
        set_fields: Dict[str, Any] = {
            "status": to_status,
            "updated_at": utcnow(),
        }
        if extra_set:
            set_fields.update(extra_set)
        doc = await self.collection.find_one_and_update(
            {"_id": oid, "status": from_status},
            {"$set": set_fields},
            return_document=ReturnDocument.AFTER,
        )
        if not doc:
            return None
        payload = dict(doc)
        payload["id"] = payload.pop("_id")
        return CreditReservation.model_validate(payload)

    async def list_expired_pending(
        self, *, now: Optional[datetime] = None, limit: int = 200
    ) -> List[CreditReservation]:
        now = now or utcnow()
        cursor = self.collection.find(
            {
                "status": ReservationStatus.PENDING.value,
                "expires_at": {"$lte": now},
            }
        ).limit(limit)
        rows = await cursor.to_list(length=limit)
        out: List[CreditReservation] = []
        for doc in rows:
            payload = dict(doc)
            payload["id"] = payload.pop("_id")
            out.append(CreditReservation.model_validate(payload))
        return out


class CreditLedgerRepository:
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self.collection = collection

    async def ensure_indexes(self) -> None:
        await self.collection.create_index(
            [("account_id", 1), ("created_at", 1)],
            name="credit_ledger_account_created",
        )
        await self.collection.create_index(
            [("job_id", 1)], name="credit_ledger_job"
        )
        # Idempotency key for compensating ops (optional sparse unique).
        await self.collection.create_index(
            [("reservation_id", 1), ("reason", 1)],
            name="credit_ledger_reservation_reason",
            unique=True,
            sparse=True,
        )
        # Idempotency key for Stripe subscription grants.
        await self.collection.create_index(
            [("metadata.stripe_invoice_id", 1)],
            name="credit_ledger_stripe_invoice_unique",
            unique=True,
            sparse=True,
        )
        # Idempotency key for calendar / unified period grants.
        await self.collection.create_index(
            [("metadata.period_grant_key", 1)],
            name="credit_ledger_period_grant_unique",
            unique=True,
            sparse=True,
        )

    async def append(self, entry: CreditLedgerEntry) -> CreditLedgerEntry:
        """Append-only insert. Never update/delete."""
        payload = entry.model_dump(by_alias=True)
        payload["_id"] = ObjectId(payload["_id"])
        payload["account_id"] = ObjectId(str(payload["account_id"]))
        payload["user_id"] = ObjectId(str(payload["user_id"]))
        if payload.get("reservation_id"):
            payload["reservation_id"] = ObjectId(str(payload["reservation_id"]))
        if payload.get("settlement_id"):
            payload["settlement_id"] = ObjectId(str(payload["settlement_id"]))
        try:
            await self.collection.insert_one(payload)
            return entry
        except DuplicateKeyError:
            # Check if this was a reservation idempotent release
            if payload.get("reservation_id"):
                existing = await self.collection.find_one(
                    {
                        "reservation_id": payload.get("reservation_id"),
                        "reason": entry.reason,
                    }
                )
                if existing:
                    p = dict(existing)
                    p["id"] = p.pop("_id")
                    return CreditLedgerEntry.model_validate(p)
            
            # Duplicate period / stripe grant keys: bubble up for caller idempotency.
            meta = payload.get("metadata") or {}
            if meta.get("stripe_invoice_id") or meta.get("period_grant_key"):
                raise

            raise

    async def sum_deltas_for_job(self, job_id: str) -> int:
        pipeline = [
            {"$match": {"job_id": job_id}},
            {"$group": {"_id": None, "total": {"$sum": "$delta"}}},
        ]
        rows = await self.collection.aggregate(pipeline).to_list(length=1)
        if not rows:
            return 0
        return int(rows[0].get("total") or 0)


class JobSettlementRepository:
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self.collection = collection

    async def ensure_indexes(self) -> None:
        await self.collection.create_index(
            [("job_id", 1)], unique=True, name="job_settlement_job_unique"
        )

    async def get_by_job_id(self, job_id: str) -> Optional[JobSettlement]:
        doc = await self.collection.find_one({"job_id": job_id})
        if not doc:
            return None
        payload = dict(doc)
        payload["id"] = payload.pop("_id")
        return JobSettlement.model_validate(payload)

    async def create(self, settlement: JobSettlement) -> JobSettlement:
        payload = settlement.model_dump(by_alias=True)
        payload["_id"] = ObjectId(payload["_id"])
        payload["user_id"] = ObjectId(str(payload["user_id"]))
        if payload.get("reservation_id"):
            payload["reservation_id"] = ObjectId(str(payload["reservation_id"]))
        try:
            await self.collection.insert_one(payload)
            return settlement
        except DuplicateKeyError:
            existing = await self.get_by_job_id(settlement.job_id)
            if existing:
                return existing
            raise


def billing_collections(db: AsyncIOMotorDatabase) -> dict[str, AsyncIOMotorCollection]:
    return {
        "accounts": db.get_collection("credit_accounts"),
        "reservations": db.get_collection("credit_reservations"),
        "ledger": db.get_collection("credit_ledger"),
        "settlements": db.get_collection("job_settlements"),
        "usage": db.get_collection("usage_records"),
        "costs": db.get_collection("cost_records"),
    }
