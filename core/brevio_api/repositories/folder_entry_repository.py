import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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


def data_result_to_mongo(result: DataResult) -> Dict[str, Any]:
    """Serialize a DataResult for $push. Always persist ObjectId _id.

    model_dump(exclude_unset=True) drops default_factory _id, so later
    positional updates on results._id match nothing.
    """
    payload = result.model_dump(by_alias=True, exclude_none=True)
    result_id = result.id
    if not isinstance(result_id, ObjectId):
        result_id = ObjectId(str(result_id))
    payload["_id"] = result_id
    return payload


def _canonical_result_oid(result_id: Any) -> ObjectId:
    if isinstance(result_id, ObjectId):
        return result_id
    if isinstance(result_id, str) and ObjectId.is_valid(result_id):
        return ObjectId(result_id)
    raise ValueError("Invalid result ID format")


def _index_of_data_result(
    results: List[Dict[str, Any]], result_id: Any, fields: Dict[str, Any]
) -> int | None:
    target = str(result_id)
    for index, row in enumerate(results):
        stored = row.get("_id")
        if stored is not None and str(stored) == target:
            return index
    orphans: List[int] = []
    for index, row in enumerate(results):
        if row.get("_id") is not None:
            continue
        orphans.append(index)
        if fields.get("index") is not None and row.get("index") == fields["index"]:
            return index
        location = fields.get("download_location")
        if location and row.get("download_location") == location:
            return index
        name = fields.get("name")
        if name and row.get("name") == name:
            return index
    if len(orphans) == 1:
        return orphans[0]
    return None


class FolderEntryRepository:
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self.collection = collection
        logger.info("FolderEntryRepository initialized successfully")

    async def create_folder_entry(self, entry: FolderEntry) -> FolderEntry:
        try:
            entry_dict = entry.model_dump()
            entry_dict["_id"] = ObjectId(entry_dict["_id"])
            entry_dict["user_id"] = ObjectId(entry_dict["user_id"])
            folder_ref = entry_dict.get("library_folder_id")
            if folder_ref:
                entry_dict["library_folder_id"] = ObjectId(str(folder_ref))
            else:
                entry_dict["library_folder_id"] = None

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

    async def update_data_result(
        self,
        folder_entry_id: str,
        result_id: Any,
        fields: Dict[str, Any],
    ) -> FolderEntry:
        if not ObjectId.is_valid(folder_entry_id):
            raise ValueError("Invalid entry ID format")
        try:
            entry = await self.collection.find_one({"_id": ObjectId(folder_entry_id)})
            if not entry:
                raise ValueError("Folder entry not found")
            results = entry.get("results") or []
            if not isinstance(results, list):
                raise ValueError("DataResult not found in folder entry")
            index = _index_of_data_result(results, result_id, fields)
            if index is None:
                raise ValueError("DataResult not found in folder entry")
            set_fields = {
                f"results.{index}.{key}": value for key, value in fields.items()
            }
            set_fields[f"results.{index}._id"] = _canonical_result_oid(result_id)
            set_fields["updated_at"] = datetime.now(timezone.utc)
            result = await self.collection.update_one(
                {"_id": ObjectId(folder_entry_id)},
                {"$set": set_fields},
            )
            if result.matched_count == 0:
                raise ValueError("DataResult not found in folder entry")
            return await self.get_folder_entry_by_id(folder_entry_id)
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Database error updating data result: {e}", exc_info=True)
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
            query = {
                "_id": {"$in": entries_refs},
                "user_id": ObjectId(user_id),
            }
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

    async def ensure_indexes(self) -> None:
        await self.collection.create_index(
            [("user_id", 1), ("library_folder_id", 1)],
            name="entries_user_library_folder",
        )

    async def get_entries_by_user(
        self, user_id: str, library_folder_id: Optional[str] = None
    ) -> List[FolderEntry]:
        if not ObjectId.is_valid(user_id):
            raise ValueError("Invalid user ID format")
        try:
            query: Dict[str, Any] = {"user_id": ObjectId(user_id)}
            if library_folder_id == "unfiled":
                query["$or"] = [
                    {"library_folder_id": None},
                    {"library_folder_id": {"$exists": False}},
                ]
            elif library_folder_id:
                if not ObjectId.is_valid(library_folder_id):
                    raise ValueError("Invalid folder ID format")
                query["library_folder_id"] = ObjectId(library_folder_id)
            raw = self.collection.find(query)
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

    async def count_by_library_folders(self, user_id: str) -> Dict[str, int]:
        pipeline = [
            {"$match": {"user_id": ObjectId(user_id)}},
            {
                "$group": {
                    "_id": "$library_folder_id",
                    "count": {"$sum": 1},
                }
            },
        ]
        counts: Dict[str, int] = {"unfiled": 0}
        async for row in self.collection.aggregate(pipeline):
            key = row.get("_id")
            if key is None:
                counts["unfiled"] += int(row.get("count") or 0)
            else:
                counts[str(key)] = int(row.get("count") or 0)
        return counts

    async def clear_library_folder(self, user_id: str, folder_id: str) -> int:
        result = await self.collection.update_many(
            {
                "user_id": ObjectId(user_id),
                "library_folder_id": ObjectId(folder_id),
            },
            {
                "$set": {
                    "library_folder_id": None,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return int(result.modified_count)

    async def set_library_folder(
        self,
        user_id: str,
        entry_ids: List[ObjectId],
        folder_id: Optional[ObjectId],
    ) -> int:
        result = await self.collection.update_many(
            {"_id": {"$in": entry_ids}, "user_id": ObjectId(user_id)},
            {
                "$set": {
                    "library_folder_id": folder_id,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return int(result.matched_count)
