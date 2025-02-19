from datetime import datetime, timedelta
from pydantic import EmailStr
import random
from datetime import datetime, timezone
from backend.models.user.data_result import DataResult
from backend.models.user.folder_entry import FolderEntry
from backend.repositories.user_repository import UserRepository
from ..models.user.user import User
class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repo = user_repository

    def get_user_by_id(self, user_id: str) -> User:
        return self.user_repo.get_user_by_id(user_id)

    def get_user_by_email(self, email: EmailStr) -> User:
        return self.user_repo.get_user_by_field("email",email)

    def get_user_by_username(self, username: str) -> User:
        return self.user_repo.get_user_by_field("username", username)

    def create_user(self, user: User) -> User:
        if self.user_repo.get_user_by_field("email",user.email) or self.user_repo.get_user_by_field("username",user.username):
            raise ValueError("User already exists")
        
        return self.user_repo.create_user(user)

    def initiate_password_recovery(self, email: EmailStr) -> None:
        user = self.user_repo.get_user_by_field("email",email)
        if not user:
            return

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

    def verify_otp(self, email: EmailStr, otp_code: str) -> bool:
        user = self.user_repo.get_user_by_field("email", email)

        if not user:
            raise ValueError("User not found")

        if user.otp != otp_code or datetime.now(timezone.utc) > user.exp:
            return False

        self.user_repo.password_recovery_handshake(
            email=email,
            update_user={"is_otp_verified": True}
        )

        return True

    def change_password(self, email: EmailStr, new_password: str) -> User:
        updated_user = self.user_repo.change_password(
            email,
            password = new_password
        )

        return updated_user
    
    def create_folder_entry(self, user_id: str, name: str = "") -> FolderEntry:
        user = self.user_repo.get_user_by_id(user_id)

        if not user:
            raise ValueError("User not found")

        entry = FolderEntry()
    
        user.folder.entries.append(entry)
        self.user_repo.update_user(user)

        return entry

    def create_data_result(self, user_id: str, folder_entry: FolderEntry, result: DataResult) -> DataResult:
        user = self.user_repo.get_user_by_id(user_id)
        
        user_folder_entry = next(
            (entry for entry in user.folder.entries if entry.id == folder_entry.id),
            None
        )
        
        if not user_folder_entry:
            raise ValueError("FolderEntry no encontrado en el usuario")
        
        user_folder_entry.results.append(result)
        self.user_repo.update_user(user)
        return result