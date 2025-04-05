from typing import Optional, Type

from bson import ObjectId
from pydantic import Field, field_validator

from .base_model import BaseModel


class DataResult(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    index: Optional[int] = None
    url: Optional[str] = None
    download_location: Optional[str] = None
    name: Optional[str] = Field(
        None, strict=True, max_length=100, description="Name of the data result"
    )
    duration: Optional[float] = 0.0

    @field_validator("download_location", mode="before")
    @classmethod
    def validate_download_location(cls: Type["DataResult"], v: Optional[str]) -> str:
        if not v:
            raise ValueError("Download location cannot be empty.")
        if not v.startswith("audios/"):
            raise ValueError("Download location should start with 'audios/'.")
        return v
