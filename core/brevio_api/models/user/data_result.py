from typing import Optional, Type

from bson import ObjectId
from pydantic import ConfigDict, Field, field_validator

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

    model_config = ConfigDict(arbitrary_types_allowed=True)

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
