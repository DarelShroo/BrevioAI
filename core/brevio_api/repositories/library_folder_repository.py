import logging
from datetime import datetime, timezone
from typing import List, Optional

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from core.brevio_api.models.user.library_folder import LibraryFolder

logger = logging.getLogger(__name__)


class LibraryFolderRepository:
    def __init__(self, collection) -> None:
        self.collection = collection

    async def ensure_indexes(self) -> None:
        await self.collection.create_index(
            [("user_id", 1), ("name_key", 1)],
            unique=True,
            name="unique_library_folder_name_per_user",
        )
        await self.collection.create_index([("user_id", 1)], name="library_folder_user")

    async def create(self, folder: LibraryFolder) -> LibraryFolder:
        payload = folder.model_dump()
        payload["_id"] = ObjectId(payload["_id"])
        payload["user_id"] = ObjectId(payload["user_id"])
        try:
            result = await self.collection.insert_one(payload)
        except DuplicateKeyError as exc:
            raise ValueError("duplicate") from exc
        payload["_id"] = result.inserted_id
        return LibraryFolder.model_validate(payload)

    async def get_by_id(self, folder_id: str) -> Optional[LibraryFolder]:
        if not ObjectId.is_valid(folder_id):
            return None
        doc = await self.collection.find_one({"_id": ObjectId(folder_id)})
        if not doc:
            return None
        return LibraryFolder.model_validate(doc)

    async def list_for_user(self, user_id: str) -> List[LibraryFolder]:
        cursor = self.collection.find({"user_id": ObjectId(user_id)}).sort(
            "name_key", 1
        )
        docs = await cursor.to_list(length=None)
        return [LibraryFolder.model_validate(doc) for doc in docs]

    async def rename(
        self, folder_id: str, user_id: str, name: str, name_key: str
    ) -> LibraryFolder:
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(folder_id), "user_id": ObjectId(user_id)},
                {
                    "$set": {
                        "name": name,
                        "name_key": name_key,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
        except DuplicateKeyError as exc:
            raise ValueError("duplicate") from exc
        if result.matched_count == 0:
            raise ValueError("missing")
        updated = await self.get_by_id(folder_id)
        if updated is None:
            raise ValueError("missing")
        return updated

    async def delete(self, folder_id: str, user_id: str) -> bool:
        result = await self.collection.delete_one(
            {"_id": ObjectId(folder_id), "user_id": ObjectId(user_id)}
        )
        return result.deleted_count > 0
