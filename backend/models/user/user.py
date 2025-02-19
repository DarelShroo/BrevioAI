from typing import Optional
from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field

from backend.models.user.user_folder import UserFolder

class User(BaseModel):
    id: Optional[ObjectId] = Field(default_factory=ObjectId, alias="_id")
    username: str
    email: EmailStr
    password: str
    folder: UserFolder
    otp: Optional[int] = None
    exp: Optional[int] = None

    class Config:
        arbitrary_types_allowed = True  # Permite tipos arbitrarios como ObjectId
        populate_by_name = True

    def to_dict(self):
        user_dict = {
            "username": self.username,
            "email": self.email,
            "password": self.password,
            "folder": self.folder.model_dump(),
            "otp": self.otp,
            "exp": self.exp
        }
        if self.id is not None:
            user_dict["_id"] = self.id
        return user_dict
