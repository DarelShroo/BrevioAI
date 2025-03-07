from datetime import datetime, timedelta, timezone
from pydantic import EmailStr
import random
from backend.models.user.data_result import DataResult
from backend.models.user.folder_entry import FolderEntry
from backend.repositories.user_repository import UserRepository
from ..models.user.user import User
from fastapi import HTTPException, status

class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repo = user_repository

    def get_user_by_id(self, user_id: str) -> User:
        try:
            user = self.user_repo.get_user_by_id(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            return user
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving user by ID: {str(e)}"
            )

    def get_user_by_email(self, email: EmailStr) -> User:
        try:
            user = self.user_repo.get_user_by_field("email", email)
            return user
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving user by email: {str(e)}"
            )

    def get_user_by_username(self, username: str) -> User:
        try:
            user = self.user_repo.get_user_by_field("username", username)
            return user
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving user by username: {str(e)}"
            )

    def create_user(self, user: User) -> User:
        try:
            if self.user_repo.get_user_by_field("email", user.email) or self.user_repo.get_user_by_field("username", user.username):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User already exists"
                )

            return self.user_repo.create_user(user)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating user: {str(e)}"
            )

    def initiate_password_recovery(self, email: EmailStr) -> None:
        try:
            user = self.user_repo.get_user_by_field("email", email)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            otp_code = str(random.randint(100000, 999999))
            otp_expiration = datetime.utcnow() + timedelta(minutes=10)

            self.user_repo.password_recovery_handshake(
                email=email,
                update_user={
                    "otp_code": otp_code,
                    "otp_expiration": otp_expiration,
                    "is_otp_verified": False
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error initiating password recovery: {str(e)}"
            )

    def verify_otp(self, email: EmailStr, otp_code: str) -> bool:
        try:
            user = self.user_repo.get_user_by_field("email", email)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            if user.otp != otp_code or datetime.now(timezone.utc) > user.otp_expiration:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired OTP"
                )

            self.user_repo.password_recovery_handshake(
                email=email,
                update_user={"is_otp_verified": True}
            )

            return True
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error verifying OTP: {str(e)}"
            )

    def change_password(self, email: EmailStr, new_password: str) -> User:
        try:
            user = self.user_repo.get_user_by_field("email", email)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            updated_user = self.user_repo.change_password(
                email,
                password=new_password
            )

            return updated_user
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error changing password: {str(e)}"
            )
    
    def create_folder_entry(self, user_id: str, name: str = "") -> FolderEntry:
        try:
            user = self.user_repo.get_user_by_id(user_id)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            entry = FolderEntry()
            user.folder.entries.append(entry)
            self.user_repo.update_user(user)

            return entry
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating folder entry: {str(e)}"
            )

    def create_data_result(self, user_id: str, folder_entry_id: str, result: DataResult) -> DataResult:
        try:
            user = self.user_repo.get_user_by_id(user_id)
            
            folder_entries = {entry.id: entry for entry in user.folder.entries}
            
            user_folder_entry = folder_entries.get(folder_entry_id)
            
            if not user_folder_entry:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="FolderEntry not found"
                )
            
            user_folder_entry.results.append(result)
            self.user_repo.update_user(user)
            return result
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating data result: {str(e)}"
            )
