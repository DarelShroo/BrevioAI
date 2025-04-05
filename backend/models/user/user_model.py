from typing import Any, Dict, Optional

from bson import ObjectId
from pydantic import EmailStr, Field

from .base_model import BaseModel
from .user_folder import UserFolder


class User(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    username: str = Field("", strict=True, min_length=6, max_length=20)
    email: EmailStr
    password: str
    folder: UserFolder
    otp: Optional[int] = None
    exp: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        user_dict: Dict[str, Any] = {
            "username": self.username,
            "email": self.email,
            "password": self.password,
            "folder": self.folder.model_dump(),
            "otp": self.otp,
            "exp": self.exp,
        }
        user_dict["_id"] = self.id
        return user_dict
