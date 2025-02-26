import os
from typing import Optional
from pydantic import Field, field_validator
from bson import ObjectId
from .base_model import BaseModel

class DataResult(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId)
    index: Optional[int] = None
    url: Optional[str] = None 
    download_location: Optional[str] = None
    name: Optional[str] = Field(None, strict=True, max_length=100)
    duration: Optional[float] = 0.0

    @field_validator('download_location')
    def validate_download_location(cls, v):
        if not v:
            raise ValueError("Download location cannot be empty.")
        if not v.startswith("audios/"):
            raise ValueError("Download location should start with 'audios/'.")
        return v
    
data_result = DataResult()