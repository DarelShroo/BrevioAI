import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument
from pydantic import ValidationError

from core.brevio_api.models.user.folder_entry import FolderEntry
from core.shared.enums.job_status import JobStatus, can_transition_status
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
            # Omit null keys so the partial unique index never sees nulls.
            if not entry_dict.get("idempotency_key"):
                entry_dict.pop("idempotency_key", None)

            serialized_results = []
            for result in entry.results or []:
                serialized_results.append(data_result_to_mongo(result))
            entry_dict["results"] = serialized_results

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
            # Preserve DuplicateKeyError for idempotency races.
            from pymongo.errors import DuplicateKeyError

            if isinstance(e, DuplicateKeyError):
                raise
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
        await self._ensure_idempotency_index()
        await self.collection.create_index(
            [("status", 1), ("queued_at", 1)],
            name="entries_status_queued_at",
        )
        await self.collection.create_index(
            [("status", 1), ("claimed_at", 1)],
            name="entries_status_claimed_at",
        )

    async def _ensure_idempotency_index(self) -> None:
        """Unique (user_id, idempotency_key) only when a real key is present.

        Sparse unique indexes still index explicit ``null`` values, so older
        entries with ``idempotency_key: null`` blocked index builds and crashed
        ``GET /users/folders``. Unset nulls and use a partial filter instead.
        """
        await self.collection.update_many(
            {"idempotency_key": None},
            {"$unset": {"idempotency_key": ""}},
        )
        desired_filter = {"idempotency_key": {"$type": "string"}}
        try:
            existing = await self.collection.index_information()
        except Exception:
            existing = {}
        current = existing.get("entries_user_idempotency")
        # Keep any unique partial index; only rebuild the legacy sparse one.
        if current and current.get("unique") and current.get("partialFilterExpression"):
            return
        if current is not None:
            try:
                await self.collection.drop_index("entries_user_idempotency")
            except Exception:
                logger.warning(
                    "event=drop_idempotency_index_failed",
                    exc_info=True,
                )
        await self.collection.create_index(
            [("user_id", 1), ("idempotency_key", 1)],
            name="entries_user_idempotency",
            unique=True,
            partialFilterExpression=desired_filter,
        )

    async def find_by_idempotency_key(
        self, user_id: str, idempotency_key: str
    ) -> Optional[FolderEntry]:
        if not idempotency_key or not ObjectId.is_valid(user_id):
            return None
        doc = await self.collection.find_one(
            {
                "user_id": ObjectId(user_id),
                "idempotency_key": idempotency_key,
            }
        )
        if not doc:
            return None
        payload = dict(doc)
        payload["id"] = str(payload.pop("_id"))
        return FolderEntry.model_validate(payload)

    async def claim_queued_job(self, job_id: str) -> Optional[FolderEntry]:
        """Atomic QUEUED → PROCESSING. Returns None if another worker won."""
        if not ObjectId.is_valid(job_id):
            return None
        now = datetime.now(timezone.utc)
        doc = await self.collection.find_one_and_update(
            {
                "_id": ObjectId(job_id),
                "status": JobStatus.QUEUED.value,
            },
            {
                "$set": {
                    "status": JobStatus.PROCESSING.value,
                    "claimed_at": now,
                    "heartbeat_at": now,
                    "updated_at": now,
                    "results.$[r].status": JobStatus.PROCESSING.value,
                }
            },
            array_filters=[{"r.status": JobStatus.QUEUED.value}],
            return_document=ReturnDocument.AFTER,
        )
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return FolderEntry.model_validate(doc)

    async def mark_job_enqueued(self, job_id: str) -> Optional[FolderEntry]:
        if not ObjectId.is_valid(job_id):
            return None
        now = datetime.now(timezone.utc)
        doc = await self.collection.find_one_and_update(
            {"_id": ObjectId(job_id)},
            {
                "$set": {"enqueued_at": now, "updated_at": now},
                "$inc": {"enqueue_attempts": 1},
            },
            return_document=ReturnDocument.AFTER,
        )
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return FolderEntry.model_validate(doc)

    async def touch_job_heartbeat(self, job_id: str) -> None:
        if not ObjectId.is_valid(job_id):
            return
        await self.collection.update_one(
            {"_id": ObjectId(job_id), "status": JobStatus.PROCESSING.value},
            {"$set": {"heartbeat_at": datetime.now(timezone.utc)}},
        )

    async def transition_job_status(
        self,
        job_id: str,
        *,
        new_status: str,
        from_statuses: Optional[List[str]] = None,
        error_message: str | None = None,
    ) -> Optional[FolderEntry]:
        """Atomic job-level status transition with can_transition_status guard."""
        if not ObjectId.is_valid(job_id):
            return None
        entry = await self.get_folder_entry_by_id(job_id)
        current = entry.status
        if not can_transition_status(current, new_status):
            logger.info(
                "event=job_status_transition_rejected job_id=%s current=%s new=%s",
                job_id,
                current,
                new_status,
            )
            return None
        if current == new_status:
            return entry
        filt: Dict[str, Any] = {"_id": ObjectId(job_id)}
        if from_statuses is not None:
            filt["status"] = {"$in": from_statuses}
        elif current is not None:
            filt["status"] = current
        else:
            filt["$or"] = [{"status": None}, {"status": {"$exists": False}}]
        now = datetime.now(timezone.utc)
        set_fields: Dict[str, Any] = {
            "status": new_status,
            "updated_at": now,
        }
        doc = await self.collection.find_one_and_update(
            filt,
            {"$set": set_fields},
            return_document=ReturnDocument.AFTER,
        )
        if not doc:
            return None
        if error_message and new_status == JobStatus.FAILED.value:
            # Best-effort annotate open results without demoting COMPLETED.
            results = doc.get("results") or []
            for index, row in enumerate(results):
                row_status = row.get("status")
                if row_status in (
                    JobStatus.COMPLETED.value,
                    JobStatus.FAILED.value,
                ):
                    continue
                if row_status and not can_transition_status(
                    row_status, JobStatus.FAILED.value
                ):
                    continue
                await self.collection.update_one(
                    {"_id": ObjectId(job_id)},
                    {
                        "$set": {
                            f"results.{index}.status": JobStatus.FAILED.value,
                            f"results.{index}.phase": JobStatus.FAILED.value,
                            f"results.{index}.success": False,
                            f"results.{index}.error_message": error_message,
                            f"results.{index}.error_code": "JOB_RECOVERED",
                            f"results.{index}.error_type": "JobAbandoned",
                        }
                    },
                )
            doc = await self.collection.find_one({"_id": ObjectId(job_id)})
            if not doc:
                return None
        doc["id"] = str(doc.pop("_id"))
        return FolderEntry.model_validate(doc)

    async def list_jobs_by_status(
        self, statuses: List[str], *, limit: int = 200
    ) -> List[FolderEntry]:
        cursor = self.collection.find({"status": {"$in": statuses}}).limit(limit)
        rows = await cursor.to_list(length=limit)
        entries: List[FolderEntry] = []
        for entry in rows:
            entry["id"] = str(entry.pop("_id"))
            entries.append(FolderEntry.model_validate(entry))
        return entries

    async def upsert_data_result_by_index(
        self,
        folder_entry_id: str,
        result: DataResult,
    ) -> DataResult:
        """Ensure one logical DataResult per (job, index). Reuses existing _id."""
        if not ObjectId.is_valid(folder_entry_id):
            raise ValueError("Invalid entry ID format")
        if result.index is None:
            raise ValueError("DataResult.index is required for upsert")
        entry = await self.collection.find_one({"_id": ObjectId(folder_entry_id)})
        if not entry:
            raise ValueError("Folder entry not found")
        results = entry.get("results") or []
        existing_index = None
        existing_id = None
        for i, row in enumerate(results):
            if row.get("index") == result.index:
                existing_index = i
                existing_id = row.get("_id")
                break
        payload = data_result_to_mongo(result)
        if existing_id is not None:
            payload["_id"] = (
                existing_id
                if isinstance(existing_id, ObjectId)
                else ObjectId(str(existing_id))
            )
            current_status = results[existing_index].get("status")
            new_status = payload.get("status")
            if new_status and not can_transition_status(current_status, new_status):
                # Keep existing terminal identity; return as-is.
                result.id = payload["_id"]
                result.status = current_status
                return result
            set_fields = {
                f"results.{existing_index}.{key}": value
                for key, value in payload.items()
            }
            set_fields["updated_at"] = datetime.now(timezone.utc)
            await self.collection.update_one(
                {"_id": ObjectId(folder_entry_id)},
                {"$set": set_fields},
            )
            result.id = payload["_id"]
            return result
        await self.collection.update_one(
            {"_id": ObjectId(folder_entry_id)},
            {
                "$push": {"results": payload},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
        )
        return result

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
