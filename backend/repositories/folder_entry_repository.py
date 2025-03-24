import logging
from fastapi import HTTPException
from mongomock import Database
from pydantic import ValidationError
from pymongo.errors import PyMongoError

from backend.models.user.folder_entry import FolderEntry

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class FolderEntryRepository:
    def __init__(self, db: Database):
        try:
            if not isinstance(db, Database):
                raise ValueError("Invalid database instance provided")
            self.db_entry = db
            self.collection = self.db_entry["entries"]
            logger.info("FolderEntryRepository initialized successfully")
        except ValueError as e:
            logger.error(f"Initialization failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database initialization error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during initialization: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Unexpected initialization error: {str(e)}")

    def create_folder_entry(self, folder_entry: FolderEntry) -> FolderEntry:
        try:
            logger.debug("Creating FolderEntry")
            folder_entry_dict = folder_entry.model_dump()
            inserted_id = self.collection.insert_one(folder_entry_dict).inserted_id
            folder_entry_dict["_id"] = inserted_id
            created_folder_entry = FolderEntry(**folder_entry_dict)
            logger.info(f"FolderEntry created successfully with ID: {inserted_id}")
            return created_folder_entry
        except ValidationError as e:
            logger.error(f"Invalid FolderEntry data: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid FolderEntry data: {str(e)}")
        except PyMongoError as e:
            logger.error(f"Database error creating FolderEntry: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error creating FolderEntry: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")