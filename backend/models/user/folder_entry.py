from .data_result import DataResult
from pydantic import Field
from typing import List
from bson import ObjectId
from .base_model import BaseModel

class FolderEntry(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId)
    results: List[DataResult] = []

    def to_dict(self):
        return {
            "_id": self.id if self.id else ObjectId(),
            "results": [result.model_dump() for result in self.results]
        }