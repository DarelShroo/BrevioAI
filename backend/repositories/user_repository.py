from typing import Optional
from bson import ObjectId
from pymongo import ReturnDocument

from backend.utils.data_mapper import generate_obj_if_data_exist
from ..models.user.user import User
from pymongo.database import Database
from pydantic import EmailStr
from ..utils.password_utils import hash_password
from pymongo.errors import PyMongoError
from bson.errors import InvalidId


class UserRepository:
    def __init__(self, db: Database):
        self.db_user = db
        self.collection = self.db_user["users"]

    def get_user_by_id(self, id: str) -> Optional[User]:
        try:
            user_dict = self.collection.find_one({"_id": ObjectId(id)})
            return generate_obj_if_data_exist(user_dict, User)
        except InvalidId as e:
            raise ValueError(
                f"The following error occurred when getting the user: {e}")

    def get_user_by_field(self, field: str, value: str) -> Optional[User]:
        try:
            user_dict = self.collection.find_one({field: value})
            return generate_obj_if_data_exist(user_dict, User)
        except PyMongoError as e:
            raise RuntimeError(f"The following error occurred: {e}")

    def password_recovery_handshake(self, email: EmailStr, user: User) -> Optional[User]:
        user_dict = self.collection.find_one_and_update({"email": email}, {"$set": user},
                                                        return_document=ReturnDocument.AFTER)
        return generate_obj_if_data_exist(user_dict, User)

    def change_password(self, email: EmailStr, password: str) -> Optional[User]:
        user_dict = self.collection.find_one_and_update({"email": email}, {
                                                        "$set": {"password": hash_password(password), "exp": 0, "otp": None}},
                                                        return_document=ReturnDocument.AFTER)
        return generate_obj_if_data_exist(user_dict, User)

    def create_user(self, user: User) -> User:
        try:
            user_dict = user.to_dict()
            inserted_id = self.collection.insert_one(user_dict).inserted_id
            user_dict["_id"] = inserted_id
            return User(**user_dict)
        except PyMongoError as e:
            raise RuntimeError(f"Error when creating user: {e}")

    def update_user(self, user: User) -> Optional[User]:
        try:
            user_id = ObjectId(user.id) if ObjectId.is_valid(user.id) else None
            if not user_id:
                raise ValueError("Invalid user id")
            user_dict_updated = self.collection.find_one_and_update({"_id" : user_id}, {
                "$set": user.to_dict()},
                return_document=ReturnDocument.AFTER)
            
            return generate_obj_if_data_exist(user_dict_updated, User)
        
        except (PyMongoError, ValueError) as e:
            raise RuntimeError(f"Error when updating user: {e}")
