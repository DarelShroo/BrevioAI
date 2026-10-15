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


from core.brevio_api.models.errors.api_codes import ApiErrorCode


class AuthWithPassword(BaseModel):
    password: str

    @field_validator("password")
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError(ApiErrorCode.PASSWORD_TOO_SHORT.value)
        if not re.search(r"[A-Z]", value):
            raise ValueError(ApiErrorCode.PASSWORD_NO_UPPERCASE.value)
        if not re.search(r"[a-z]", value):
            raise ValueError(ApiErrorCode.PASSWORD_NO_LOWERCASE.value)
        if not re.search(r"\d", value):
            raise ValueError(ApiErrorCode.PASSWORD_NO_DIGIT.value)
        if not re.search(r"[\W_]", value):
            raise ValueError(ApiErrorCode.PASSWORD_NO_SPECIAL.value)
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
            raise ValueError(ApiErrorCode.INVALID_IDENTITY_FORMAT.value)

        return value
