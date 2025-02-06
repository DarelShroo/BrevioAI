from ..models.user.register_user import RegisterUser
from ..models.user.user import User
from pymongo.database import Database
from pydantic import EmailStr
import random
from datetime import timedelta, datetime
from ..models.user.recovery_password_otp import RecoveryPasswordOtp
from ..utils.password_utils import hash_password

class UserRepository:
    def __init__(self, db: Database):
        self.db_user = db
        self.collection = self.db_user["users"]

    def get_user_by_id(self, id: str) -> User:
        return self.collection.find_one({"_id": id})

    def get_user_by_email(self, email: str) -> User:
        try:
            return self.collection.find_one({"email": email})
        except Exception as e:
            raise Exception(f"The following error occurred: {e}")

    def get_user_by_username(self, username: str) -> User:
        try:
            user: User = self.collection.find_one({"username": username})
            return user
        except Exception as e:
            raise Exception(f"The following error occurred: {e}")
        
    def password_recovery_handshake(self, email: EmailStr, update_user: dict) -> User:
        user: User = self.collection.update_one({"email": email}, {"$set": update_user})
        return user
    def change_password(self, email: EmailStr,  password: str, exp: int):
        user: User = self.collection.update_one({"email": email}, {"$set": {"password": password, "exp": exp}})
        return user

    def create_user(self, user_register: RegisterUser) -> User:
        try:
            result = self.collection.insert_one(user_register.to_dict())
            return self.collection.find_one({"_id": result.inserted_id})
        except Exception as e:
            raise Exception(f"The following error occurred: {e}")
