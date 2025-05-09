import logging
from typing import Any, Dict, List, Union

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from mongomock.database import Database as MongomockDatabase
from pydantic import ValidationError
from pymongo.database import Database
from pymongo.errors import PyMongoError

from core.brevio_api.models.user.folder_entry import FolderEntry
from core.shared.models.user.data_result import DataResult

logger = logging.getLogger(__name__)

INVALID_ID_MSG = "Invalid ID format"
DB_ERROR_MSG = "Database error"
NOT_FOUND_MSG = "FolderEntry not found"


class FolderEntryRepository:
    def __init__(self, db: Union[Database, MongomockDatabase]) -> None:
        try:
            self.collection = db["entries"]
            logger.info("FolderEntryRepository initialized successfully")
        except AttributeError as e:
            logger.error(
                f"Initialization failed: Invalid database instance provided - {str(e)}"
            )
            raise HTTPException(status_code=500, detail="Database initialization error")
        except Exception as e:
            logger.error(
                f"Unexpected error during initialization: {str(e)}", exc_info=True
            )
            raise HTTPException(status_code=500, detail="Internal server error")

    async def create_folder_entry(self, entry: FolderEntry) -> FolderEntry:
        try:
            logger.debug(f"Creating FolderEntry for user ID: {entry.user_id}")
            entry_dict = await entry.to_mongo()
            inserted_id = self.collection.insert_one(entry_dict).inserted_id
            created_entry = FolderEntry(**entry_dict)
            logger.info(f"FolderEntry created with ID: {inserted_id}")
            return created_entry
        except ValidationError as e:
            logger.error(f"Invalid folder entry data: {str(e)}")
            raise HTTPException(
                status_code=400, detail=f"Invalid folder entry data: {str(e)}"
            )
        except PyMongoError as e:
            logger.error(f"Database error creating folder entry: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    async def get_folder_entry_by_id(self, entry_id: ObjectId) -> FolderEntry:
        try:
            if isinstance(entry_id, str):
                try:
                    entry_id = ObjectId(entry_id)
                except InvalidId:
                    logger.error(f"Invalid ID format: {entry_id}")
                    raise HTTPException(
                        status_code=400, detail="Invalid folder entry ID format"
                    )

            logger.debug(f"Fetching FolderEntry with ID: {entry_id}")
            entry_data = self.collection.find_one({"_id": entry_id})
            return FolderEntry.model_validate(entry_data)
        except InvalidId:
            logger.error(f"Invalid ID format: {entry_id}")
            raise HTTPException(
                status_code=400, detail="Invalid folder entry ID format"
            )
        except ValidationError as e:
            logger.error(f"Validation error for folder entry data: {str(e)}")
            raise HTTPException(
                status_code=400, detail=f"Invalid folder entry data: {str(e)}"
            )
        except PyMongoError as e:
            logger.error(f"Database error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    async def update_folder_entry(
        self, entry_id: ObjectId, update_data: Dict[str, Any]
    ) -> FolderEntry:
        try:
            if isinstance(entry_id, str):
                try:
                    entry_id = ObjectId(entry_id)
                except InvalidId:
                    logger.error(f"Invalid ID format: {entry_id}")
                    raise HTTPException(
                        status_code=400, detail="Invalid folder entry ID format"
                    )

            logger.debug(f"Updating FolderEntry {entry_id} with data: {update_data}")

            init_result = self.collection.update_one(
                {"_id": entry_id, "results": {"$exists": False}},
                {"$set": {"results": []}},
                upsert=False,
            )

            update_operations = {}
            for key, value in update_data.items():
                if key.startswith("$"):
                    update_operations[key] = value
                else:
                    if not update_operations.get("$set"):
                        update_operations["$set"] = {}
                    update_operations["$set"][key] = value

            if update_operations:
                result = self.collection.update_one(
                    {"_id": entry_id}, update_operations
                )

                logger.debug(
                    f"Update result: matched={result.matched_count}, modified={result.modified_count}"
                )

                if result.matched_count == 0:
                    logger.warning(f"No FolderEntry found with ID: {entry_id}")
                    raise HTTPException(status_code=404, detail=NOT_FOUND_MSG)

            updated_entry = self.collection.find_one({"_id": entry_id})
            if not updated_entry:
                logger.error(f"Could not retrieve updated entry with ID: {entry_id}")
                raise HTTPException(
                    status_code=500, detail="Could not retrieve updated entry"
                )
            if updated_entry is not None and isinstance(updated_entry, dict):
                results = updated_entry.get("results", [])
                if results is not None and isinstance(results, list):
                    updated_entry["results"] = [
                        DataResult.model_validate(result).model_dump()
                        for result in results
                    ]

            return FolderEntry.model_validate(updated_entry)

        except PyMongoError as e:
            logger.error(
                f"Database error updating folder entry: {str(e)}", exc_info=True
            )
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    async def get_entries_ids_by_user_id(
        self, _user_id: ObjectId, _entries_refs: List[ObjectId]
    ) -> List[FolderEntry]:
        try:
            logger.info(
                f"Searching for {len(_entries_refs)} entries for user {_user_id}"
            )

            for entry_id in _entries_refs:
                if not isinstance(entry_id, ObjectId):
                    logger.error(f"Invalid ObjectId: {entry_id}")
                    raise HTTPException(
                        status_code=400, detail=f"Invalid ObjectId: {entry_id}"
                    )

            query = {"_id": {"$in": _entries_refs}, "user_id": _user_id}

            found_entries = list(self.collection.find(query))

            logger.info(f"Found {len(found_entries)} matching entries")

            return [FolderEntry.model_validate(entry) for entry in found_entries]

        except ValidationError as e:
            logger.error(f"Invalid folder entry data: {str(e)}")
            raise HTTPException(
                status_code=400, detail=f"Invalid folder entry data: {str(e)}"
            )
        except PyMongoError as e:
            logger.error(f"Database error fetching entries: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching entries: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    async def delete_folder_entry(self, entry_id: ObjectId) -> Dict[str, str]:
        try:
            if not ObjectId.is_valid(entry_id):
                raise HTTPException(status_code=400, detail=INVALID_ID_MSG)

            result = self.collection.delete_one({"_id": entry_id})
            if result.deleted_count == 0:
                raise HTTPException(status_code=404, detail=NOT_FOUND_MSG)
            logger.info(f"FolderEntry deleted: {entry_id}")
            return {"message": "FolderEntry eliminado exitosamente"}
        except HTTPException:
            raise
        except PyMongoError as e:
            logger.error(f"Database error: {str(e)}")
            raise HTTPException(status_code=500, detail=DB_ERROR_MSG)

    async def get_entries_by_user(self, user_id: ObjectId) -> List[FolderEntry]:
        try:
            if not ObjectId.is_valid(user_id):
                raise HTTPException(status_code=400, detail="Invalid user ID format")

            return [
                FolderEntry.model_validate(entry)
                for entry in self.collection.find({"user_id": user_id})
            ]
        except HTTPException as e:
            raise e
        except PyMongoError as e:
            logger.error(f"Database error for user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=DB_ERROR_MSG)
