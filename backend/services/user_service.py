import logging
import random
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import HTTPException, status
from pydantic import EmailStr, ValidationError
from pymongo.errors import PyMongoError

from backend.models.user.folder_entry_ref import FolderEntryRef
from backend.models.user.user_folder import UserFolder
from utils.password_utils import hash_password

from ..models.user import DataResult, FolderEntry, User
from ..repositories import UserRepository
from ..repositories.folder_entry_repository import FolderEntryRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class UserService:
    def __init__(
        self, user_repository: UserRepository, folder_entry_repo: FolderEntryRepository
    ):
        self.user_repo = user_repository
        self._folder_entry_repo = folder_entry_repo
        logger.info("UserService initialized with UserRepository")

    def get_user_by_id(self, user_id: ObjectId) -> User | None:
        try:
            logger.debug(f"Fetching user with ID: {user_id}")
            user = self.user_repo.get_user_by_field("_id", user_id)
            if not user:
                logger.warning(f"No user found with ID: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )
            logger.info(f"User retrieved successfully with ID: {user_id}")

            return user
        except Exception as e:
            logger.error(
                f"Error retrieving user by ID {user_id}: {str(e)}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving user by ID: {str(e)}",
            )

    def get_user_by_email(self, email: EmailStr) -> User | None:
        try:
            logger.debug(f"Fetching user with email: {email}")
            user = self.user_repo.get_user_by_field("email", email)
            logger.info(f"User found with email: {email}")

            return user
        except Exception as e:
            logger.error(
                f"Error retrieving user by email {email}: {str(e)}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving user by email: {str(e)}",
            )

    def get_user_by_username(self, username: str) -> User | None:
        try:
            logger.debug(f"Fetching user with username: {username}")
            user = self.user_repo.get_user_by_field("username", username)
            if not user:
                logger.warning(f"No user found with username: {username}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )

            logger.info(f"User found with username: {username}")

            return user
        except Exception as e:
            logger.error(
                f"Error retrieving user by username {username}: {str(e)}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving user by username: {str(e)}",
            )

    def create_user(self, user: User) -> User:
        try:
            logger.debug("Creating new user")
            user_exist = self.user_repo.get_user_by_field(
                "email", user.email
            ) or self.user_repo.get_user_by_field("username", user.username)
            if user_exist:
                logger.warning(
                    f"User already exists with email: {user.email} or username: {user.username}"
                )
                raise HTTPException(status_code=400, detail="User already exists")
            created_user = self.user_repo.create_user(user)
            logger.info(f"User created successfully with ID: {created_user.id}")
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

    def initiate_password_recovery(self, email: EmailStr) -> None:
        try:
            logger.debug(f"Initiating password recovery for email: {email}")
            user = self.user_repo.get_user_by_field("email", email)
            if not user:
                logger.warning(f"No user found with email: {email}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )

            otp_code = str(random.randint(100000, 999999))
            otp_expiration = datetime.now(timezone.utc) + timedelta(minutes=10)

            self.user_repo.update_user(
                user.id,
                {
                    "otp": otp_code,
                    "exp": otp_expiration,
                },
            )
            logger.info(
                f"Password recovery initiated for email: {email}, OTP: {otp_code}"
            )
        except Exception as e:
            logger.error(
                f"Error initiating password recovery for email {email}: {str(e)}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error initiating password recovery: {str(e)}",
            )

    def verify_otp(self, email: EmailStr, otp_code: str) -> bool:
        try:
            logger.debug(f"Verifying OTP for email: {email}, OTP: {otp_code}")
            user = self.user_repo.get_user_by_field("email", email)
            if not user:
                logger.warning(f"No user found with email: {email}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )

            if user.otp != otp_code:
                logger.warning(f"Invalid OTP for email: {email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid OTP",
                )

            if user.exp is None:
                logger.warning(f"Missing expiration for email: {email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OTP expiration not set",
                )

            if datetime.now(timezone.utc) > datetime.fromtimestamp(
                user.exp, timezone.utc
            ):
                logger.warning(f"Expired OTP for email: {email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Expired OTP",
                )

            self.user_repo.update_user(user.id, {"is_otp_verified": True})
            logger.info(f"OTP verified successfully for email: {email}")
            return True
        except Exception as e:
            logger.error(
                f"Error verifying OTP for email {email}: {str(e)}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error verifying OTP: {str(e)}",
            )

    def change_password(self, email: EmailStr, new_password: str) -> User:
        try:
            logger.debug(f"Changing password for email: {email}")
            user = self.user_repo.get_user_by_field("email", email)
            if not user:
                logger.warning(f"No user found with email: {email}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )

            updated_user = self.user_repo.update_user(
                user.id,
                {"password": hash_password(new_password), "otp": None, "exp": 0},
            )

            if not updated_user:
                logger.warning(f"Failed to change password for email: {email}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to change password",
                )
            logger.info(f"Password changed successfully for email: {email}")

            return updated_user
        except Exception as e:
            logger.error(
                f"Error changing password for email {email}: {str(e)}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error changing password: {str(e)}",
            )

    def create_folder_entry(self, user_id: ObjectId) -> FolderEntryRef:
        try:
            logger.debug(f"Creating FolderEntry for user ID: {user_id}")

            user = self.user_repo.get_user_by_field("_id", str(user_id))

            if not user:
                logger.warning(f"No user found with ID: {user_id}")
                raise HTTPException(status_code=404, detail="User not found")

            if user.folder is None:
                user.folder = UserFolder(_id=ObjectId(), entries=[])
            elif user.folder.entries is None:
                user.folder.entries = []

            entry = FolderEntry(_id=ObjectId(), user_id=user.id, name="", results=[])
            entry = self._folder_entry_repo.create_folder_entry(entry)
            entry_ref = FolderEntryRef(_id=ObjectId(entry.id))

            user.folder.entries.append(entry_ref)

            update_data = {
                "folder.entries": [
                    entry.model_dump(by_alias=True) for entry in user.folder.entries
                ]
            }

            self.user_repo.update_user(user.id, update_data)

            logger.info(
                f"FolderEntry {entry_ref.id} created and linked to user {user_id}"
            )

            return entry_ref
        except Exception as e:
            logger.error(
                f"Error creating FolderEntry for user {user_id}: {str(e)}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500, detail=f"Error creating FolderEntry: {str(e)}"
            )

    def create_data_result(
        self, user_id: ObjectId, folder_entry_id: ObjectId, result: DataResult
    ) -> DataResult:
        try:
            logger.debug(
                f"Creating DataResult for user ID: {user_id}, FolderEntry ID: {folder_entry_id}"
            )
            user = self.user_repo.get_user_by_field("_id", str(user_id))

            if not user:
                logger.warning(f"No user found with ID: {user_id}")
                raise HTTPException(status_code=404, detail="User not found")

            folder_entry: FolderEntry | None = (
                self._folder_entry_repo.get_folder_entry_by_id(folder_entry_id)
            )
            if not folder_entry:
                logger.warning(
                    f"FolderEntry not found. Requested ID: {folder_entry_id}"
                )
                raise HTTPException(
                    status_code=404,
                    detail=f"FolderEntry with ID {folder_entry_id} not found",
                )

            result_dict = result.model_dump(by_alias=True, exclude_unset=True)

            update_result = self._folder_entry_repo.update_folder_entry(
                folder_entry.id, {"$push": {"results": result_dict}}
            )

            if not update_result:
                raise HTTPException(
                    status_code=500, detail="Failed to update FolderEntry"
                )

            logger.info(
                f"DataResult added to FolderEntry {folder_entry_id} for user {user_id}"
            )
            return result
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error creating DataResult: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Error creating DataResult: {str(e)}"
            )
