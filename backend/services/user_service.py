from datetime import datetime, timedelta, timezone
from pydantic import EmailStr, ValidationError
import random
import logging
from fastapi import HTTPException, status
from ..models.user import DataResult, FolderEntry, User
from ..repositories import UserRepository
from pymongo.errors import PyMongoError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repo = user_repository
        logger.info("UserService initialized with UserRepository")

    def get_user_by_id(self, user_id: str) -> User:
        try:
            logger.debug(f"Fetching user with ID: {user_id}")
            user = self.user_repo.get_user_by_id(user_id)
            if not user:
                logger.warning(f"No user found with ID: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            logger.info(f"User retrieved successfully with ID: {user_id}")
            return user
        except Exception as e:
            logger.error(f"Error retrieving user by ID {user_id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving user by ID: {str(e)}"
            )

    def get_user_by_email(self, email: EmailStr) -> User:
        try:
            logger.debug(f"Fetching user with email: {email}")
            user = self.user_repo.get_user_by_field("email", email)
            if user:
                logger.info(f"User found with email: {email}")
            else:
                logger.warning(f"No user found with email: {email}")
            return user
        except Exception as e:
            logger.error(f"Error retrieving user by email {email}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving user by email: {str(e)}"
            )

    def get_user_by_username(self, username: str) -> User:
        try:
            logger.debug(f"Fetching user with username: {username}")
            user = self.user_repo.get_user_by_field("username", username)
            if user:
                logger.info(f"User found with username: {username}")
            else:
                logger.warning(f"No user found with username: {username}")
            return user
        except Exception as e:
            logger.error(f"Error retrieving user by username {username}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving user by username: {str(e)}"
            )

    def create_user(self, user: User) -> User:
        try:
            logger.debug("Creating new user")
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
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            otp_code = str(random.randint(100000, 999999))
            otp_expiration = datetime.now(timezone.utc) + timedelta(minutes=10)

            self.user_repo.password_recovery_handshake(
                email=email,
                update_user={
                    "otp_code": otp_code,
                    "otp_expiration": otp_expiration,
                    "is_otp_verified": False
                }
            )
            logger.info(f"Password recovery initiated for email: {email}, OTP: {otp_code}")
        except Exception as e:
            logger.error(f"Error initiating password recovery for email {email}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error initiating password recovery: {str(e)}"
            )

    def verify_otp(self, email: EmailStr, otp_code: str) -> bool:
        try:
            logger.debug(f"Verifying OTP for email: {email}, OTP: {otp_code}")
            user = self.user_repo.get_user_by_field("email", email)
            if not user:
                logger.warning(f"No user found with email: {email}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            if user.otp != otp_code or datetime.now(timezone.utc) > user.otp_expiration:
                logger.warning(f"Invalid or expired OTP for email: {email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired OTP"
                )

            self.user_repo.update_user(
                user.id,
                {"is_otp_verified": True}
            )
            logger.info(f"OTP verified successfully for email: {email}")
            return True
        except Exception as e:
            logger.error(f"Error verifying OTP for email {email}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error verifying OTP: {str(e)}"
            )

    def change_password(self, email: EmailStr, new_password: str) -> User:
        try:
            logger.debug(f"Changing password for email: {email}")
            user = self.user_repo.get_user_by_field("email", email)
            if not user:
                logger.warning(f"No user found with email: {email}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            updated_user = self.user_repo.update_user(
                user.id,
                {"password": new_password}
            )
            logger.info(f"Password changed successfully for email: {email}")
            return updated_user
        except Exception as e:
            logger.error(f"Error changing password for email {email}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error changing password: {str(e)}"
            )

    def create_folder_entry(self, user_id: str) -> FolderEntry:
        try:
            logger.debug(f"Creating FolderEntry for user ID: {user_id}")
            # Obtener el usuario
            user = self.user_repo.get_user_by_id(user_id)
            if not user:
                logger.warning(f"No user found with ID: {user_id}")
                raise HTTPException(status_code=404, detail="User not found")
            
            new_entry = FolderEntry()

            user.folder.entries.append(new_entry)
            
            self.user_repo.update_user(
                user.id, 
                {"folder.entries": [entry.model_dump(by_alias=True) for entry in user.folder.entries]}
            )
            
            logger.info(f"FolderEntry {new_entry.id} creado y vinculado al usuario {user_id}")
            return new_entry
        except Exception as e:
            logger.error(f"Error creando FolderEntry para usuario {user_id}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error creando FolderEntry: {str(e)}")

    def create_data_result(self, user_id: str, folder_entry_id: str, result: DataResult) -> DataResult:
        try:
            logger.debug(f"Creating DataResult for user ID: {user_id}, FolderEntry ID: {folder_entry_id}")
            user = self.user_repo.get_user_by_id(user_id)
            if not user:
                logger.warning(f"No user found with ID: {user_id}")
                raise HTTPException(status_code=404, detail="User not found")
            
            folder_entries = {entry.id: entry for entry in user.folder.entries}
            user_folder_entry = folder_entries.get(folder_entry_id)
            if not user_folder_entry:
                available_ids = list(folder_entries.keys())
                logger.warning(f"FolderEntry not found. Available IDs: {available_ids}, Requested ID: {folder_entry_id}")
                raise HTTPException(status_code=404, detail=f"FolderEntry with ID {folder_entry_id} not found")
            
            user_folder_entry.results.append(result)
            self.user_repo.update_user(
                user.id,
                {"folder.entries": [entry.model_dump(by_alias=True) for entry in user.folder.entries]}
            )
            logger.info(f"DataResult added to FolderEntry {folder_entry_id} for user {user_id}")
            return result
        except Exception as e:
            logger.error(f"Error creating DataResult for user {user_id}, FolderEntry {folder_entry_id}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error creating DataResult: {str(e)}")