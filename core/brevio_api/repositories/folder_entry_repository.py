import logging
from typing import Any, Dict, List

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import ValidationError

from core.brevio_api.models.user.folder_entry import FolderEntry
from core.shared.models.user.data_result import DataResult

logger = logging.getLogger(__name__)

INVALID_ID_MSG = "Invalid ID format"
DB_ERROR_MSG = "Database error"
NOT_FOUND_MSG = "FolderEntry not found"


class FolderEntryRepository:
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self.collection = collection
        logger.info("FolderEntryRepository initialized successfully")

    async def create_folder_entry(self, entry: FolderEntry) -> FolderEntry:
        try:
            entry_dict = entry.model_dump()
            entry_dict["_id"] = ObjectId(entry_dict["_id"])
            entry_dict["user_id"] = ObjectId(entry_dict["user_id"])

            result = await self.collection.insert_one(entry_dict)
            entry_dict["_id"] = result.inserted_id

            folder_entry_obj = FolderEntry.model_validate(entry_dict)

            folder_entry_obj.id = entry_dict.pop("_id")
            folder_entry_obj.user_id = entry_dict["user_id"]

            return folder_entry_obj

        except ValidationError as e:
            logger.error(f"Validation error creating folder entry: {e}")
            raise ValueError(f"Invalid folder entry data: {e}")
        except Exception as e:
            logger.error(f"Database error creating folder entry: {e}", exc_info=True)
            # Translate database errors to HTTP 500
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {e}",
            )

    async def get_folder_entry_by_id(self, entry_id: str) -> FolderEntry:
        if not ObjectId.is_valid(entry_id):
            raise ValueError("Invalid entry ID format")
        try:
            entry_data = await self.collection.find_one({"_id": ObjectId(entry_id)})
        except Exception as e:
            logger.error(f"Database error fetching folder entry: {e}", exc_info=True)
            raise RuntimeError(f"Database error: {e}")

        if not entry_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND_MSG
            )

        try:
            folder_entry_obj = FolderEntry.model_validate(entry_data)
            return folder_entry_obj
        except ValidationError as e:
            logger.error(f"Validation error fetching folder entry: {e}")
            raise ValueError(f"Invalid folder entry data: {e}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Database error fetching folder entry: {e}", exc_info=True)
            raise RuntimeError(f"Database error: {e}")

    async def update_folder_entry(
        self, entry_id: str, update_data: Dict[str, Any]
    ) -> FolderEntry:
        if not ObjectId.is_valid(entry_id):
            raise ValueError("Invalid entry ID format")
        try:
            if update_data:
                result = await self.collection.update_one(
                    {"_id": ObjectId(entry_id)}, update_data
                )
                if result.matched_count == 0:
                    raise ValueError("Folder entry not found")
            updated_entry = await self.collection.find_one({"_id": ObjectId(entry_id)})
            if not updated_entry:
                raise RuntimeError("Could not retrieve updated entry")

            results = updated_entry.get("results", [])
            if results and isinstance(results, list):
                updated_entry["results"] = [
                    DataResult.model_validate(r).model_dump() for r in results
                ]

            updated_entry["id"] = str(updated_entry.pop("_id"))

            return FolderEntry.model_validate(updated_entry)
        except ValidationError as e:
            logger.error(f"Validation error updating folder entry: {e}")
            raise ValueError(str(e))
        except Exception as e:
            logger.error(f"Database error updating folder entry: {e}", exc_info=True)
            raise RuntimeError(f"Database error: {e}")

    async def get_entries_ids_by_user_id(
        self, user_id: str, entries_refs: List[ObjectId]
    ) -> List[FolderEntry]:
        if not ObjectId.is_valid(user_id):
            raise ValueError("Invalid user ID format")

        for entry_id in entries_refs:
            if not isinstance(entry_id, ObjectId):
                raise ValueError(f"Invalid ObjectId: {entry_id}")

        try:
            query = {"_id": {"$in": entries_refs}}
            raw = self.collection.find(query)
            found_entries = await raw.to_list(length=None)

            for entry in found_entries:
                entry["id"] = str(entry.pop("_id"))
            return [FolderEntry.model_validate(entry) for entry in found_entries]
        except HTTPException:
            raise
        except ValidationError as e:
            logger.error(f"Validation error fetching entries: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Validation error fetching entries: {e}",
            )
        except Exception as e:
            logger.error(f"Database error fetching entries: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error fetching entries: {e}",
            )

    async def delete_folder_entry(self, entry_id: str) -> Dict[str, str]:
        if not ObjectId.is_valid(entry_id):
            raise ValueError(INVALID_ID_MSG)
        try:
            result = await self.collection.delete_one({"_id": ObjectId(entry_id)})
            if result.deleted_count == 0:
                raise ValueError(NOT_FOUND_MSG)
            logger.info(f"FolderEntry deleted: {entry_id}")
            return {"message": "FolderEntry eliminado exitosamente"}

        except Exception as e:
            logger.error(f"Database error deleting entry: {e}", exc_info=True)
            raise RuntimeError(f"Database error: {e}")

    async def get_entries_by_user(self, user_id: str) -> List[FolderEntry]:
        if not ObjectId.is_valid(user_id):
            raise ValueError("Invalid user ID format")
        try:
            raw = self.collection.find({"user_id": ObjectId(user_id)})
            entries = await raw.to_list(length=None)

            for entry in entries:
                entry["id"] = str(entry.pop("_id"))

            return [FolderEntry.model_validate(entry) for entry in entries]
        except HTTPException:
            raise
        except ValidationError as e:
            logger.error(f"Validation error fetching entries by user: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Validation error fetching entries by user: {e}",
            )
        except Exception as e:
            logger.error(f"Database error fetching entries by user: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error fetching entries by user: {e}",
            )
