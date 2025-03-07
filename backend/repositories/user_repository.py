import logging
from typing import Optional
from bson import ObjectId
from pymongo import ReturnDocument
from fastapi import HTTPException
from pymongo.database import Database
from pymongo.errors import PyMongoError
from bson.errors import InvalidId
from pydantic import EmailStr
from backend.utils.data_mapper import generate_obj_if_data_exist
from ..models.user.user import User
from ..utils.password_utils import hash_password

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class UserRepository:
    def __init__(self, db: Database):
        """
        Initialize UserRepository with a MongoDB database instance.

        Args:
            db (Database): MongoDB database instance.

        Raises:
            HTTPException: If database connection is invalid.
        """
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
        """
        Retrieve a user by their ID.

        Args:
            id (str): User ID as a string.

        Returns:
            Optional[User]: User object if found, None otherwise.

        Raises:
            HTTPException: 400 if ID format is invalid, 500 for database errors.
        """
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
        """
        Retrieve a user by a specific field value.

        Args:
            field (str): Field name to query (e.g., 'email').
            value (str): Value to search for.

        Returns:
            Optional[User]: User object if found, None otherwise.

        Raises:
            HTTPException: 500 for database errors.
        """
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

    def password_recovery_handshake(self, email: EmailStr, user: User) -> Optional[User]:
        try:
            logger.debug(f"Starting password recovery handshake for email: {email}")
            user_dict = self.collection.find_one_and_update(
                {"email": email}, {"$set": user},
                return_document=ReturnDocument.AFTER
            )
            updated_user = generate_obj_if_data_exist(user_dict, User)
            if updated_user:
                logger.info(f"Password recovery handshake successful for email: {email}")
            else:
                logger.warning(f"No user found for password recovery with email: {email}")
            return updated_user
        except PyMongoError as e:
            logger.error(f"Database error during password recovery for {email}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during password recovery for {email}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    def change_password(self, email: EmailStr, password: str) -> Optional[User]:
        try:
            logger.debug(f"Changing password for email: {email}")
            user_dict = self.collection.find_one_and_update(
                {"email": email}, 
                {"$set": {"password": hash_password(password), "exp": 0, "otp": None}},
                return_document=ReturnDocument.AFTER
            )
            updated_user = generate_obj_if_data_exist(user_dict, User)
            if updated_user:
                logger.info(f"Password changed successfully for email: {email}")
            else:
                logger.warning(f"No user found to change password for email: {email}")
            return updated_user
        except PyMongoError as e:
            logger.error(f"Database error changing password for {email}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error changing password for {email}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    def create_user(self, user: User) -> User:
        try:
            logger.debug("Creating new user")
            user_dict = user.to_dict()
            inserted_id = self.collection.insert_one(user_dict).inserted_id
            user_dict["_id"] = inserted_id
            created_user = User(**user_dict)
            logger.info(f"User created successfully with ID: {inserted_id}")
            return created_user
        except ValueError as e:
            logger.error(f"Invalid user data: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid user data: {str(e)}")
        except PyMongoError as e:
            logger.error(f"Database error creating user: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error creating user: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    def update_user(self, user: User) -> Optional[User]:
        try:
            logger.debug(f"Updating user with ID: {user.id}")
            user_id = ObjectId(user.id) if ObjectId.is_valid(user.id) else None
            if not user_id:
                raise HTTPException(status_code=400, detail="Invalid user ID format")

            user_dict_updated = self.collection.find_one_and_update(
                {"_id": user_id}, {"$set": user.to_dict()},
                return_document=ReturnDocument.AFTER
            )
            if not user_dict_updated:
                logger.warning(f"No user found to update with ID: {user.id}")
                raise HTTPException(status_code=404, detail=f"User with ID {user.id} not found")
            
            updated_user = generate_obj_if_data_exist(user_dict_updated, User)
            logger.info(f"User updated successfully with ID: {user.id}")
            return updated_user
        except HTTPException:
            raise 
        except PyMongoError as e:
            logger.error(f"Database error updating user with ID {user.id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error updating user with ID {user.id}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")