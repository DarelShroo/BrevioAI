from typing import Any, Dict, Optional

from bson.objectid import ObjectId
from pydantic import EmailStr, Field

from ....shared.models.user.base_model import BaseModel
from .user_folder import UserFolder


class User(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    username: str = Field("", strict=True, min_length=6, max_length=25)
    email: EmailStr
    password: str
    user_credit: float = 0
    plan_id: str = "free"
    plan_version: str = "1"
    folder: Optional[UserFolder] = None
    otp: Optional[int] = None
    exp: Optional[int] = None
    otp_attempts: int = 0
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    stripe_subscription_status: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        user_dict: Dict[str, Any] = {
            "username": self.username,
            "email": self.email,
            "password": self.password,
            "user_credit": self.user_credit,
            "plan_id": self.plan_id,
            "plan_version": self.plan_version,
            "folder": self.folder_dict(),
            "otp": self.otp,
            "exp": self.exp,
            "otp_attempts": self.otp_attempts,
            "stripe_customer_id": self.stripe_customer_id,
            "stripe_subscription_id": self.stripe_subscription_id,
            "stripe_subscription_status": self.stripe_subscription_status,
        }
        user_dict["_id"] = self.id
        return user_dict

    def folder_dict(self) -> Dict[str, Any]:
        if self.folder:
            return self.folder.model_dump()
        return {}
