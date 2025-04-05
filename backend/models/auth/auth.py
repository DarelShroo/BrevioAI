from typing import Any, Dict

from pydantic import EmailStr, Field, field_validator, model_validator

from .auth_base import AuthWithPassword, IdentityBase


class LoginUser(AuthWithPassword, IdentityBase):
    pass


class RegisterUser(AuthWithPassword):
    username: str = Field("", strict=True, max_length=100)
    email: EmailStr

    @model_validator(mode="before")
    def check_username_length(cls, values: dict[str, Any]) -> dict[str, Any]:
        username = values.get("username")
        if username and len(username) < 6:
            raise ValueError("El nombre de usuario debe tener al menos 6 caracteres.")
        return values

    def to_dict(self) -> Dict[str, Any]:  # Fixed annotation at line 32
        return self.model_dump(exclude_unset=True)


class RecoveryPasswordOtp(AuthWithPassword):
    email: EmailStr
    password: str
    otp: int


class UserIdentity(IdentityBase):
    pass


class RecoveryPassword(UserIdentity):
    pass
