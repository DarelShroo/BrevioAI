import logging
from typing import Dict, List, Optional, Union

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from mongomock.database import Database as MongomockDatabase
from pydantic import ValidationError
from pymongo.database import Database
from pymongo.errors import PyMongoError

from models.user.folder_entry import FolderEntry

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

    def create_folder_entry(self, folder_entry: FolderEntry) -> FolderEntry:
        try:
            logger.debug(f"Creating folder entry: {folder_entry}")
            folder_entry_dict = folder_entry.model_dump(
                exclude={"id"}, exclude_unset=True
            )
            result = self.collection.insert_one(folder_entry_dict)
            folder_entry.id = result.inserted_id
            logger.info(f"FolderEntry created with ID: {result.inserted_id}")
            return folder_entry
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except PyMongoError as e:
            logger.error(f"Database error: {str(e)}")
            raise HTTPException(status_code=500, detail=DB_ERROR_MSG)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")

    def get_folder_entry_by_id(self, entry_id: ObjectId) -> Optional[FolderEntry]:
        try:
            entry = self.collection.find_one({"_id": entry_id})
            if not entry:
                logger.warning(f"FolderEntry not found: {entry_id}")
                raise HTTPException(status_code=404, detail=NOT_FOUND_MSG)
            return FolderEntry(**entry)
        except PyMongoError as e:
            logger.error(f"Database error: {str(e)}")
            raise HTTPException(status_code=500, detail=DB_ERROR_MSG)

    def get_all_folder_entries(self) -> List[FolderEntry]:
        try:
            return [FolderEntry(**entry) for entry in self.collection.find()]
        except PyMongoError as e:
            logger.error(f"Database error: {str(e)}")
            raise HTTPException(status_code=500, detail=DB_ERROR_MSG)

    def update_folder_entry(self, entry_id: ObjectId, update_data: dict) -> FolderEntry:
        try:
            logger.debug(f"Updating folder entry {entry_id} with data: {update_data}")

            if not ObjectId.is_valid(entry_id):
                logger.error(f"Invalid ID format: {entry_id}")
                raise HTTPException(status_code=400, detail=INVALID_ID_MSG)

            current_entry: FolderEntry = self.get_folder_entry_by_id(entry_id)

            updated_entry = None

            if current_entry is not None:
                updated_entry = current_entry.model_copy(update=update_data)
                updated_dict = updated_entry.model_dump(
                    by_alias=True,
                    exclude_unset=True,
                    exclude={"id"},
                )

            result = self.collection.update_one(
                {"_id": entry_id}, {"$set": updated_dict}
            )

            if result.modified_count == 0:
                logger.warning(f"No changes detected for entry {entry_id}")
                return current_entry

            logger.info(f"FolderEntry {entry_id} updated successfully")
            return self.get_folder_entry_by_id(entry_id)

        except HTTPException:
            raise
        except ValidationError as e:
            logger.error(f"Validation error updating entry {entry_id}: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except PyMongoError as e:
            logger.error(f"Database error updating entry {entry_id}: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Database update failed: {str(e)}"
            )
        except Exception as e:
            logger.error(
                f"Unexpected error updating entry {entry_id}: {str(e)}", exc_info=True
            )
            raise HTTPException(status_code=500, detail="Internal server error")

    def delete_folder_entry(self, entry_id: ObjectId) -> Dict[str, str]:
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

    def get_entries_by_user(self, user_id: ObjectId) -> List[FolderEntry]:
        try:
            if not ObjectId.is_valid(user_id):
                raise HTTPException(status_code=400, detail="Invalid user ID format")

            return [
                FolderEntry(**entry)
                for entry in self.collection.find({"user_id": user_id})
            ]
        except HTTPException as e:
            raise e
        except PyMongoError as e:
            logger.error(f"Database error for user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=DB_ERROR_MSG)
