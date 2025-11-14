import re
from typing import Union

from email_validator import EmailNotValidError
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    ValidationError,
    field_validator,
    validate_email,
)

from core.brevio_api.utils.email_utils import isEmail


class AuthWithPassword(BaseModel):
    password: str

    @field_validator("password")
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres.")
        if not re.search(r"[A-Z]", value):
            raise ValueError("La contraseña debe tener al menos una letra mayúscula.")
        if not re.search(r"[a-z]", value):
            raise ValueError("La contraseña debe tener al menos una letra minúscula.")
        if not re.search(r"\d", value):
            raise ValueError("La contraseña debe tener al menos un número.")
        if not re.search(r"[\W_]", value):
            raise ValueError("La contraseña debe tener al menos un carácter especial.")
        return value


USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_.-]{3,10}$")


class IdentityBase(BaseModel):
    identity: str

    @field_validator("identity")
    @classmethod
    def validate_identity(cls, value: str) -> str:
        if isEmail(value):
            return value

        if not USERNAME_REGEX.match(value):
            raise ValueError(
                "Invalid identity format: must be a valid username or email"
            )

        return value
