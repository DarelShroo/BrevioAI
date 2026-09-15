from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CredentialStatus:
    ACTIVE = "active"
    REVOKED = "revoked"


class UserCredentialBase(BaseModel):
    provider: str
    name: str = ""
    is_default: bool = False

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()


class UserCredentialCreate(UserCredentialBase):
    api_key: str


class UserCredentialResponse(UserCredentialBase):
    id: str = Field(alias="_id")
    user_id: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True)


class UserCredentialDocument(UserCredentialBase):
    id: str = Field(alias="_id")
    user_id: str
    encrypted_key: str
    status: str = CredentialStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(populate_by_name=True)
