from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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
    # Job lifecycle (FolderEntry.id is the stable job_id).
    status: Optional[str] = None
    stage: Optional[str] = None
    progress: int = 0
    queued_at: Optional[datetime] = None
    claimed_at: Optional[datetime] = None
    enqueued_at: Optional[datetime] = None
    heartbeat_at: Optional[datetime] = None
    idempotency_key: Optional[str] = None
    file_manifest: List[Dict[str, Any]] = Field(default_factory=list)
    job_payload: Optional[Dict[str, Any]] = None
    transcription_provider: Optional[str] = None
    transcription_model: Optional[str] = None
    reasoning_effort: Optional[str] = None
    enqueue_attempts: int = 0
    # FASE 5: immutable commercial plan at admission.
    plan_snapshot: Optional[Dict[str, Any]] = None
    # FASE 6: operational admission metadata (not a second status machine).
    admission_status: Optional[str] = None  # WAITING | SCHEDULED | RUNNING
    admission_reason: Optional[str] = None
    scheduled_at: Optional[datetime] = None

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
