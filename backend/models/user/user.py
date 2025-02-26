from typing import Optional
from bson import ObjectId
from fastapi import Request
from pydantic import EmailStr, Field
from .base_model import BaseModel
from backend.models.user.user_folder import UserFolder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

class User(BaseModel):
    id: Optional[ObjectId] = Field(default_factory=ObjectId, alias="_id")
    username: str = Field("", strict=True, min_length=6, max_length=20)
    email: EmailStr
    password: str
    folder: UserFolder
    otp: Optional[int] = None
    exp: Optional[int] = None

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

