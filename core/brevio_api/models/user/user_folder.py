from typing import List, Optional

from bson import ObjectId
from pydantic import Field

from .base_model import BaseModel


class UserFolder(BaseModel):
    id: Optional[ObjectId] = Field(default_factory=ObjectId, alias="_id")
    entries: List[ObjectId] = Field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "_id": str(self.id) if self.id else None,
            "entries": [str(entry) for entry in self.entries],
        }
