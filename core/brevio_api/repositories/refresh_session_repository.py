import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument

from core.brevio_api.models.user.refresh_session import RefreshSession

logger = logging.getLogger(__name__)


def _as_object_id(value: ObjectId | str) -> ObjectId:
    if isinstance(value, ObjectId):
        return value
    try:
        return ObjectId(value)
    except (InvalidId, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid user ID format") from exc


class RefreshSessionRepository:
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self.collection = collection

    async def create(self, session: RefreshSession) -> RefreshSession:
        await self.collection.insert_one(session.to_document())
        return session

    async def get_by_family(self, family_id: str) -> Optional[RefreshSession]:
        document = await self.collection.find_one({"family_id": family_id})
        if not document:
            return None
        return RefreshSession.model_validate(document)

    async def rotate(
        self,
        family_id: str,
        *,
        expected_jti: str,
        expected_token_hash: str,
        jti: str,
        token_hash: str,
        expires_at: datetime,
    ) -> Optional[RefreshSession]:
        updated = await self.collection.find_one_and_update(
            {
                "family_id": family_id,
                "revoked": False,
                "jti": expected_jti,
                "token_hash": expected_token_hash,
            },
            {
                "$set": {
                    "jti": jti,
                    "token_hash": token_hash,
                    "expires_at": expires_at,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if not updated:
            return None
        return RefreshSession.model_validate(updated)

    async def revoke_family(self, family_id: str) -> None:
        await self.collection.update_many(
            {"family_id": family_id},
            {"$set": {"revoked": True}},
        )

    async def revoke_all_for_user(self, user_id: ObjectId | str) -> None:
        await self.collection.update_many(
            {"user_id": _as_object_id(user_id)},
            {"$set": {"revoked": True}},
        )

    async def purge_expired(self) -> None:
        now = datetime.now(timezone.utc)
        try:
            await self.collection.delete_many({"expires_at": {"$lt": now}})
        except Exception:
            logger.debug("Failed to purge expired refresh sessions", exc_info=True)
