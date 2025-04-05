import logging
from typing import Any, Dict, Optional, Union

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from mongomock.database import Database as MongomockDatabase
from pydantic import ValidationError
from pymongo.database import Database
from pymongo.errors import PyMongoError

from models.user.user_model import User

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(self, db):
        try:
            self.collection = db["users"]
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Database initialization error"
            )

    def get_user_by_field(
        self, field: str, value: Union[ObjectId, str]
    ) -> Optional[User]:
        try:
            logger.debug(f"Fetching user by {field}: {value}")

            if field == "_id" and isinstance(value, str):
                if not ObjectId.is_valid(value):
                    raise HTTPException(
                        status_code=400, detail="Invalid user ID format"
                    )
                value = ObjectId(value)

            query = {field: value}
            user_data = self.collection.find_one(query)

            if not user_data:
                logger.debug(f"No user found with {field}: {value}")
                return None

            try:
                return User(**user_data)
            except ValidationError as e:
                logger.error(f"Invalid user data for {field}={value}: {str(e)}")
                return None

        except HTTPException:
            raise
        except PyMongoError as e:
            logger.error(f"Database error fetching user by {field}: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Database error while fetching user: {str(e)}"
            )

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

    def update_user(self, user_id: ObjectId, fields: Dict[str, Any]) -> Optional[User]:
        try:
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)

            existing = self.collection.find_one({"_id": user_id})
            if not existing:
                raise HTTPException(status_code=404, detail="User not found")

            result = self.collection.update_one({"_id": user_id}, {"$set": fields})

            updated_user = self.collection.find_one({"_id": user_id})
            if not updated_user:
                raise PyMongoError("Failed to retrieve updated user")

            return User(**updated_user)
        except InvalidId:
            raise HTTPException(status_code=400, detail="Invalid user ID format")
        except HTTPException:
            raise
        except PyMongoError as e:
            logger.error(f"Database error updating user: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    def delete_user(self, id: Union[ObjectId, str]) -> dict:
        try:
            logger.debug(f"Attempting to delete user with ID: {id}")
            if isinstance(id, str):
                user_id = ObjectId(id)
            else:
                user_id = id

            result = self.collection.delete_one({"_id": user_id})

            if result.deleted_count == 0:
                logger.warning(f"No user found with ID: {id} to delete")
                raise HTTPException(
                    status_code=404, detail=f"User with ID {id} not found"
                )

            logger.info(f"User with ID: {id} deleted successfully")
            return {"message": "User deleted successfully"}

        except InvalidId as e:
            logger.error(f"Invalid ID format: {id}. Error: {str(e)}")
            raise HTTPException(
                status_code=400, detail=f"Invalid user ID format: {str(e)}"
            )
        except PyMongoError as e:
            logger.error(f"Database error deleting user with ID {id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(
                f"Unexpected error deleting user with ID {id}: {str(e)}", exc_info=True
            )
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
