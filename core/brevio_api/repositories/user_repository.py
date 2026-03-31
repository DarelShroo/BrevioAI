import logging
from typing import Any, Dict, Optional, Union

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from pydantic import ValidationError
from pymongo.errors import PyMongoError

from core.brevio_api.models.odm.user_document import UserDocument
from core.brevio_api.models.user.user_model import User

logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(self, collection: Any | None = None):
        # Mantener este atributo evita romper consumidores/tests antiguos.
        self.collection = collection

    @staticmethod
    def _to_user_model(user_doc: UserDocument) -> User:
        return User(
            _id=ObjectId(str(user_doc.id)),
            username=user_doc.username,
            email=user_doc.email,
            password=user_doc.password,
            user_credit=user_doc.user_credit,
            folder=user_doc.folder,
            otp=user_doc.otp,
            exp=user_doc.exp,
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

            user_doc = await UserDocument.find_one(query)

            if not user_doc:
                logger.warning(f"No user found with {field}: {value}")
                return None

            return self._to_user_model(user_doc)

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

            user_doc = UserDocument(
                id=ObjectId(str(user.id)),
                username=user.username,
                email=user.email,
                password=user.password,
                user_credit=user.user_credit,
                folder=user.folder,
                otp=user.otp,
                exp=user.exp,
            )

            await user_doc.insert()

            logger.info(f"User created successfully with ID: {user_doc.id}")
            return self._to_user_model(user_doc)
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

            existing = await UserDocument.find_one({"_id": user_id})

            if not existing:
                raise HTTPException(status_code=404, detail="User not found")

            await existing.update({"$set": fields})

            updated_user = await UserDocument.find_one({"_id": user_id})

            if not updated_user:
                raise HTTPException(
                    status_code=500, detail="Failed to retrieve updated user"
                )

            try:
                return self._to_user_model(updated_user)
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

            user_doc = await UserDocument.find_one({"_id": user_id})
            if not user_doc:
                logger.warning(f"No user found with ID: {id} to delete")
                raise HTTPException(
                    status_code=404, detail=f"User with ID {id} not found"
                )

            await user_doc.delete()

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
