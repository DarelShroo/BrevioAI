import logging
from typing import Any, Dict, List

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException, status
from pydantic import ValidationError

from core.brevio_api.models.odm.folder_entry_document import FolderEntryDocument
from core.brevio_api.models.user.folder_entry import FolderEntry
from core.shared.models.user.data_result import DataResult

logger = logging.getLogger(__name__)

INVALID_ID_MSG = "Invalid ID format"
DB_ERROR_MSG = "Database error"
NOT_FOUND_MSG = "FolderEntry not found"


class FolderEntryRepository:
    def __init__(self, collection: Any | None = None) -> None:
        # Mantener este atributo evita romper consumidores/tests antiguos.
        self.collection = collection
        logger.info("FolderEntryRepository initialized successfully")

    @staticmethod
    def _to_folder_entry_model(entry_doc: FolderEntryDocument) -> FolderEntry:
        return FolderEntry(
            _id=ObjectId(str(entry_doc.id)),
            user_id=entry_doc.user_id,
            name=entry_doc.name,
            results=entry_doc.results,
        )

    async def create_folder_entry(self, entry: FolderEntry) -> FolderEntry:
        try:
            entry_doc = FolderEntryDocument(
                id=ObjectId(str(entry.id)),
                user_id=ObjectId(str(entry.user_id)),
                name=entry.name,
                results=entry.results,
            )
            await entry_doc.insert()

            return self._to_folder_entry_model(entry_doc)

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
            entry_doc = await FolderEntryDocument.get(ObjectId(entry_id))
        except Exception as e:
            logger.error(f"Database error fetching folder entry: {e}", exc_info=True)
            raise RuntimeError(f"Database error: {e}")

        if not entry_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND_MSG
            )

        try:
            return self._to_folder_entry_model(entry_doc)
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
            object_id = ObjectId(entry_id)
            entry_doc = await FolderEntryDocument.get(object_id)
            if not entry_doc:
                raise ValueError("Folder entry not found")

            if update_data:
                normalized_update = (
                    update_data
                    if any(key.startswith("$") for key in update_data.keys())
                    else {"$set": update_data}
                )
                await entry_doc.update(normalized_update)

            updated_entry = await FolderEntryDocument.get(object_id)
            if not updated_entry:
                raise RuntimeError("Could not retrieve updated entry")

            results = updated_entry.results
            if results and isinstance(results, list):
                sanitized_results = [
                    DataResult.model_validate(r).model_dump() for r in results
                ]
                updated_entry.results = [
                    DataResult.model_validate(result) for result in sanitized_results
                ]

            return self._to_folder_entry_model(updated_entry)
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
            found_entries = await FolderEntryDocument.find(query).to_list()
            return [self._to_folder_entry_model(entry) for entry in found_entries]
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
            entry_doc = await FolderEntryDocument.get(ObjectId(entry_id))
            if not entry_doc:
                raise ValueError(NOT_FOUND_MSG)

            await entry_doc.delete()
            logger.info(f"FolderEntry deleted: {entry_id}")
            return {"message": "FolderEntry eliminado exitosamente"}

        except Exception as e:
            logger.error(f"Database error deleting entry: {e}", exc_info=True)
            raise RuntimeError(f"Database error: {e}")

    async def get_entries_by_user(self, user_id: str) -> List[FolderEntry]:
        if not ObjectId.is_valid(user_id):
            raise ValueError("Invalid user ID format")
        try:
            entries = await FolderEntryDocument.find(
                {"user_id": ObjectId(user_id)}
            ).to_list()
            return [self._to_folder_entry_model(entry) for entry in entries]
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
