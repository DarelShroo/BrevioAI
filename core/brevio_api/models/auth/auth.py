from typing import Any, Dict

from pydantic import EmailStr, Field, field_validator, model_validator, validate_email

from core.brevio_api.models.auth.auth_base import AuthWithPassword, IdentityBase
from core.brevio_api.utils.email_utils import isEmail


class LoginUser(IdentityBase):
    password: str = Field(..., min_length=3, max_length=64)


class RegisterUser(AuthWithPassword):
    username: str = Field("", strict=True, min_length=6, max_length=25)
    email: EmailStr

    @model_validator(mode="before")
    def check_username_length(cls, values: dict[str, Any]) -> dict[str, Any]:
        username = values.get("username")
        if username and len(username) < 6:
            raise ValueError("El nombre de usuario debe tener al menos 6 caracteres.")
        return values

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class RecoveryPasswordOtp(AuthWithPassword):
    email: EmailStr
    password: str
    otp: int


class UserIdentity(IdentityBase):
    pass


class RecoveryPassword(UserIdentity):
    identity: EmailStr

    @field_validator("identity", mode="before")
    @classmethod
    def validate_email_identity(cls, value: str) -> str:
        if not isEmail(value):
            raise ValueError("Invalid identity format: must be a valid email")
        return value
