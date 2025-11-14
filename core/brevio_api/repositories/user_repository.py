import logging
from typing import Any, Dict, Optional, Union

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import ValidationError
from pymongo.errors import PyMongoError

from core.brevio_api.models.user.user_model import User

logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        try:
            self.collection = collection
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Database initialization error: {str(e)}"
            )

    async def get_user_by_field(
        self, field: str, value: Union[ObjectId, str]
    ) -> Optional[User]:
        try:
            logger.debug(f"Fetching user by {field}: {value}")

            if field == "_id" and isinstance(value, str):
                try:
                    value = ObjectId(value)
                except (InvalidId, TypeError):
                    logger.error(f"Invalid ObjectId format: {value}")
                    raise HTTPException(status_code=400, detail="Invalid ID format")

            query = {field: value}

            user_data = await self.collection.find_one(query)

            if not user_data:
                logger.warning(f"No user found with {field}: {value}")
                return None

            logger.debug(f"Raw user data from DB: {user_data}")

            try:
                if "folder" in user_data and user_data["folder"]:
                    if "entries" in user_data["folder"]:
                        user_data["folder"]["entries"] = [
                            e["_id"] if isinstance(e, dict) and "_id" in e else e
                            for e in user_data["folder"]["entries"]
                        ]

                return User(**user_data)

            except Exception as e:
                logger.error(f"Validation error: {str(e)}")
                raise HTTPException(
                    status_code=422,
                    detail={"message": "Invalid user data structure"},
                )

        except HTTPException:
            raise
        except PyMongoError as e:
            logger.error(f"Database error while fetching user: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Database error while fetching user",
            )
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error while processing user data",
            )

    async def create_user(self, user: User) -> User:
        try:
            logger.debug("Creating new user")

            user_dict = user.model_dump(by_alias=True)

            result = await self.collection.insert_one(user_dict)

            inserted_id = result.inserted_id

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

    async def update_user(
        self, user_id: ObjectId, fields: Dict[str, Any]
    ) -> Optional[User]:
        try:
            if isinstance(user_id, str):
                try:
                    user_id = ObjectId(user_id)
                except (InvalidId, TypeError):
                    logger.error(f"Invalid user_id format: {user_id}")
                    raise HTTPException(
                        status_code=400, detail="Invalid user ID format"
                    )

            for key, value in fields.items():
                if isinstance(value, str) and key.endswith("_id"):
                    try:
                        fields[key] = ObjectId(value)
                    except (InvalidId, TypeError):
                        logger.error(f"Invalid ObjectId format: {value}")
                        raise HTTPException(status_code=400, detail="Invalid ID format")

            existing = await self.collection.find_one({"_id": user_id})

            if not existing:
                raise HTTPException(status_code=404, detail="User not found")

            result = await self.collection.update_one(
                {"_id": user_id}, {"$set": fields}
            )

            updated_user = await self.collection.find_one({"_id": user_id})

            if not updated_user:
                raise HTTPException(
                    status_code=500, detail="Failed to retrieve updated user"
                )

            try:
                user_updated_obj = User.model_validate(updated_user)

                return user_updated_obj
            except ValidationError as e:
                logger.error(f"Validation error: {str(e)}")
                raise HTTPException(
                    status_code=422,
                    detail={"message": "Invalid user data structure"},
                )

        except HTTPException:
            raise
        except PyMongoError as e:
            logger.error(f"Database error updating user: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error updating user: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Unexpected error")

    async def delete_user(self, id: Union[ObjectId, str]) -> dict:
        try:
            logger.debug(f"Attempting to delete user with ID: {id}")
            if isinstance(id, str):
                user_id = ObjectId(id)
            else:
                user_id = id

            result = await self.collection.delete_one({"_id": user_id})

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
