from typing import Any, Dict, Optional

from bson import ObjectId
from pydantic import EmailStr, Field

from ....shared.models.user.base_model import BaseModel
from .user_folder import UserFolder


class User(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    username: str = Field("", strict=True, min_length=6, max_length=20)
    email: EmailStr
    password: str
    user_credit: float = 0
    folder: Optional[UserFolder] = None
    otp: Optional[int] = None
    exp: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        user_dict: Dict[str, Any] = {
            "username": self.username,
            "email": self.email,
            "password": self.password,
            "folder": self.folder_dict(),
            "otp": self.otp,
            "exp": self.exp,
        }
        user_dict["_id"] = self.id
        return user_dict

    def folder_dict(self) -> Dict[str, Any]:
        if self.folder:
            return self.folder.model_dump()
        return {}
