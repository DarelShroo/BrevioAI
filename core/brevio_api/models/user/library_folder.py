from datetime import datetime, timezone

from bson import ObjectId
from pydantic import Field, field_validator

from core.shared.utils.source_names import DISPLAY_NAME_MAX_LENGTH

from ....shared.models.user.base_model import (
    BaseModel,
    SerializedObjectId,
    validate_object_id,
)


class LibraryFolder(BaseModel):
    id: SerializedObjectId = Field(default_factory=ObjectId, alias="_id")
    user_id: SerializedObjectId
    name: str = Field(..., min_length=1, max_length=DISPLAY_NAME_MAX_LENGTH)
    name_key: str = Field(..., min_length=1, max_length=DISPLAY_NAME_MAX_LENGTH)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("user_id", mode="before")
    @classmethod
    def _user_id(cls, value):
        return validate_object_id(value)
