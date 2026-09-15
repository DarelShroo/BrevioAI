import uuid
from datetime import datetime, timezone
from typing import List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from core.brevio_api.models.user.credential_model import (
    CredentialStatus,
    UserCredentialDocument,
)
from core.brevio_api.services.encryption_service import EncryptionService

_MAX_NAME_LEN = 80


class UserCredentialRepository:
    def __init__(self, db: AsyncIOMotorDatabase, encryption_service: EncryptionService):
        self.collection = db["user_credentials"]
        self.encryption_service = encryption_service

    async def ensure_indexes(self):
        # Create a partial unique index to enforce only ONE default credential per user per provider
        await self.collection.create_index(
            [("user_id", 1), ("provider", 1)],
            unique=True,
            partialFilterExpression={
                "is_default": True,
                "status": {"$ne": CredentialStatus.REVOKED},
            },
            name="unique_default_credential",
        )
        await self.collection.create_index([("user_id", 1)])

    @staticmethod
    def normalize_name(name: Optional[str]) -> str:
        cleaned = (name or "").strip()
        if not cleaned:
            raise ValueError("Credential name is required")
        if len(cleaned) > _MAX_NAME_LEN:
            raise ValueError(
                f"Credential name must be at most {_MAX_NAME_LEN} characters"
            )
        return cleaned

    async def create_credential(
        self,
        user_id: str,
        provider: str,
        api_key: str,
        name: str,
        is_default: bool = False,
    ) -> UserCredentialDocument:
        credential_id = str(uuid.uuid4())
        display_name = self.normalize_name(name)

        existing = await self.get_active_credentials_for_user(user_id, provider)
        if not existing:
            is_default = True

        if is_default:
            # Demote others first to prevent duplicate key errors on the partial index
            await self.collection.update_many(
                {
                    "user_id": user_id,
                    "provider": provider,
                    "status": {"$ne": CredentialStatus.REVOKED},
                },
                {"$set": {"is_default": False}},
            )

        encrypted_key = self.encryption_service.encrypt(
            plaintext=api_key,
            user_id=user_id,
            credential_id=credential_id,
            provider=provider,
        )

        doc = UserCredentialDocument(
            _id=credential_id,
            user_id=user_id,
            provider=provider,
            name=display_name,
            encrypted_key=encrypted_key,
            is_default=is_default,
            status=CredentialStatus.ACTIVE,
        )

        await self.collection.insert_one(doc.model_dump(by_alias=True))
        return doc

    async def get_credential(
        self, credential_id: str
    ) -> Optional[UserCredentialDocument]:
        doc = await self.collection.find_one({"_id": credential_id})
        if doc:
            return UserCredentialDocument(**doc)
        return None

    async def get_active_credentials_for_user(
        self, user_id: str, provider: Optional[str] = None
    ) -> List[UserCredentialDocument]:
        query = {"user_id": user_id, "status": CredentialStatus.ACTIVE}
        if provider:
            query["provider"] = provider

        cursor = self.collection.find(query).sort(
            [("is_default", -1), ("updated_at", -1)]
        )
        return [UserCredentialDocument(**doc) async for doc in cursor]

    async def set_default_credential(
        self, user_id: str, credential_id: str, provider: str
    ) -> UserCredentialDocument:
        # Demote-then-Promote strategy
        await self.collection.update_many(
            {
                "user_id": user_id,
                "provider": provider,
                "status": {"$ne": CredentialStatus.REVOKED},
            },
            {"$set": {"is_default": False, "updated_at": datetime.now(timezone.utc)}},
        )
        result = await self.collection.update_one(
            {
                "_id": credential_id,
                "user_id": user_id,
                "provider": provider,
                "status": CredentialStatus.ACTIVE,
            },
            {"$set": {"is_default": True, "updated_at": datetime.now(timezone.utc)}},
        )
        if result.matched_count == 0:
            raise ValueError(f"Credential {credential_id} not found or inactive.")
        updated = await self.get_credential(credential_id)
        if updated is None:
            raise ValueError(f"Credential {credential_id} not found or inactive.")
        return updated

    async def update_credential_name(
        self,
        user_id: str,
        credential_id: str,
        name: str,
    ) -> Optional[UserCredentialDocument]:
        display_name = self.normalize_name(name)
        result = await self.collection.update_one(
            {
                "_id": credential_id,
                "user_id": user_id,
                "status": CredentialStatus.ACTIVE,
            },
            {"$set": {"name": display_name, "updated_at": datetime.now(timezone.utc)}},
        )
        if result.matched_count == 0:
            return None
        return await self.get_credential(credential_id)

    async def revoke_credential(self, credential_id: str, user_id: str) -> bool:
        current = await self.get_credential(credential_id)
        if current is None or current.user_id != user_id:
            return False

        result = await self.collection.update_one(
            {"_id": credential_id, "user_id": user_id},
            {
                "$set": {
                    "status": CredentialStatus.REVOKED,
                    "is_default": False,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        if result.matched_count == 0:
            return False

        if current.is_default:
            remaining = await self.get_active_credentials_for_user(
                user_id, current.provider
            )
            if remaining:
                await self.set_default_credential(
                    user_id, remaining[0].id, current.provider
                )
        return True

    def decrypt_credential(self, doc: UserCredentialDocument) -> str:
        return self.encryption_service.decrypt(
            encrypted_payload=doc.encrypted_key,
            user_id=doc.user_id,
            credential_id=doc.id,
            provider=doc.provider,
        )
