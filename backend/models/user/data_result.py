from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId

class DataResult(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId)
    index: Optional[int] = None
    url: Optional[str] = None
    download_location: Optional[str] = None
    name: Optional[str] = None
    duration: Optional[float] = None

    class Config:
        json_encoders = {ObjectId: str}
        arbitrary_types_allowed = True

data_result = DataResult()
