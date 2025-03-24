import logging
from typing import Optional
from bson import ObjectId
from pymongo import ReturnDocument
from fastapi import HTTPException
from pymongo.database import Database
from pymongo.errors import PyMongoError
from bson.errors import InvalidId
from pydantic import EmailStr, ValidationError
from backend.utils.data_mapper import generate_obj_if_data_exist
from ..models.user.user import User
from ..utils.password_utils import hash_password

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class UserRepository:
    def __init__(self, db: Database):
        try:
            if not isinstance(db, Database):
                raise ValueError("Invalid database instance provided")
            self.db_user = db
            self.collection = self.db_user["users"]
            logger.info("UserRepository initialized successfully")
        except ValueError as e:
            logger.error(f"Initialization failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database initialization error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during initialization: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Unexpected initialization error: {str(e)}")

    def get_user_by_id(self, id: str) -> Optional[User]:
        try:
            logger.debug(f"Fetching user by ID: {id}")
            user_dict = self.collection.find_one({"_id": ObjectId(id)})
            user = generate_obj_if_data_exist(user_dict, User)
            if user:
                logger.info(f"User found with ID: {id}")
            else:
                logger.warning(f"No user found with ID: {id}")
            return user
        except InvalidId as e:
            logger.error(f"Invalid ID format: {id}. Error: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid user ID format: {str(e)}")
        except PyMongoError as e:
            logger.error(f"Database error fetching user by ID {id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error fetching user by ID {id}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    def get_user_by_field(self, field: str, value: str) -> Optional[User]:
        try:
            logger.debug(f"Fetching user by {field}: {value}")
            user_dict = self.collection.find_one({field: value})
            user = generate_obj_if_data_exist(user_dict, User)
            if user:
                logger.info(f"User found with {field}: {value}")
            else:
                logger.warning(f"No user found with {field}: {value}")
            return user
        except PyMongoError as e:
            logger.error(f"Database error fetching user by {field}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error fetching user by {field}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    def create_user(self, user: User) -> User:
        try:
            logger.debug("Creating new user")
            
            user_dict = user.model_dump(by_alias=True)  

            inserted_id = self.collection.insert_one(user_dict).inserted_id

            created_user: User = User(**user_dict)

            logger.info(f"User created successfully with ID: {inserted_id}")
            return created_user
        except ValidationError as e:
            logger.error(f"Invalid user data: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid user data: {str(e)}")
        except PyMongoError as e:
            logger.error(f"Database error creating user: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error creating user: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


    def update_user(self, _user_id: ObjectId, fields: dict) -> Optional[User]:
        user_dict_updated = self.collection.find_one_and_update(
            {"_id": _user_id},
            {"$set": fields},
            return_document=ReturnDocument.AFTER
        )
        if not user_dict_updated:
            raise HTTPException(status_code=404, detail=f"User with ID {_user_id} not found")
        return generate_obj_if_data_exist(user_dict_updated, User)
