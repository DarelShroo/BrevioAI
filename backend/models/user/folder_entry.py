from .data_result import DataResult
from pydantic import BaseModel, Field
from typing import List, Optional
from bson import ObjectId


class FolderEntry(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId)
    results: List[DataResult] = []

    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True
        json_encoders = {ObjectId: str}

    def to_dict(self):
        return {
            "_id": self.id if self.id else ObjectId(),
            "results": [result.model_dump() for result in self.results]
        }