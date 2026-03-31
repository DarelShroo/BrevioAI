from typing import Optional

from beanie import Document
from pydantic import ConfigDict, EmailStr, Field

from core.brevio_api.models.user.user_folder import UserFolder


class UserDocument(Document):
    username: str = Field(..., min_length=6, max_length=25)
    email: EmailStr
    password: str
    user_credit: float = 0
    folder: Optional[UserFolder] = None
    otp: Optional[int] = None
    exp: Optional[int] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    class Settings:
        name = "users"
