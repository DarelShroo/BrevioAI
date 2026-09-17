from typing import Optional, Type

from bson import ObjectId
from pydantic import ConfigDict, Field, field_validator

from core.shared.enums.job_status import JobStatus

from .base_model import BaseModel, SerializedObjectId


class DataResult(BaseModel):
    id: SerializedObjectId = Field(default_factory=ObjectId, alias="_id")
    index: Optional[int] = None
    url: Optional[str] = None
    download_location: Optional[str] = None
    name: Optional[str] = Field(
        None,
        strict=True,
        max_length=255,
        description="Editable display name of the data result",
    )
    original_name: Optional[str] = Field(
        None, max_length=255, description="Immutable original source filename"
    )
    duration: Optional[float] = 0.0
    # None = legacy documents written before explicit job status existed.
    status: Optional[str] = None
    phase: Optional[str] = None
    progress: int = 0
    stage_progress: Optional[int] = None
    weight: int = 1
    success: Optional[bool] = None
    error_type: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def is_completed(self) -> bool:
        if self.status == JobStatus.COMPLETED.value:
            return True
        if self.status == JobStatus.FAILED.value:
            return False
        if self.status == JobStatus.PROCESSING.value:
            return False
        if self.success is False:
            return False
        # Legacy rows: a download_location was only written after success.
        return bool(self.download_location)

    @field_validator("download_location", mode="before")
    @classmethod
    def validate_download_location(
        cls: Type["DataResult"], v: Optional[str]
    ) -> Optional[str]:
        if v is None:
            return v
        if not v:
            raise ValueError("Download location cannot be empty.")
        if not v.startswith("data/"):
            raise ValueError("Download location should start with 'data/'.")
        return v
