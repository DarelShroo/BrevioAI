from datetime import datetime, timezone
from typing import List, Optional

from bson import ObjectId
from pydantic import Field, field_validator, model_validator

from core.shared.utils.source_names import DISPLAY_NAME_MAX_LENGTH

from ....shared.models.user.base_model import (
    BaseModel,
    SerializedObjectId,
    validate_object_id,
)
from ....shared.models.user.data_result import DataResult


class FolderEntry(BaseModel):
    id: SerializedObjectId = Field(default_factory=ObjectId, alias="_id")
    user_id: SerializedObjectId = Field(default_factory=ObjectId, alias="user_id")
    name: str = Field(default="", strict=True, max_length=DISPLAY_NAME_MAX_LENGTH)
    original_name: Optional[str] = Field(
        default=None, max_length=DISPLAY_NAME_MAX_LENGTH
    )
    library_folder_id: Optional[SerializedObjectId] = None
    results: List[DataResult] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    language: Optional[str] = None
    model: Optional[str] = None
    category: Optional[str] = None
    style: Optional[str] = None
    format: Optional[str] = None
    summary_level: Optional[str] = None
    source_type: Optional[str] = None

    @field_validator("library_folder_id", mode="before")
    @classmethod
    def _optional_folder_id(cls, value):
        if value is None or value == "":
            return None
        return validate_object_id(value)

    @model_validator(mode="after")
    def fill_created_at_from_object_id(self) -> "FolderEntry":
        """Legacy entries have no created_at; derive it from Mongo ObjectId time."""
        if self.created_at is None and isinstance(self.id, ObjectId):
            generation = self.id.generation_time
            if generation.tzinfo is None:
                generation = generation.replace(tzinfo=timezone.utc)
            self.created_at = generation
        return self
