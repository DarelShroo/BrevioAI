from typing import List, Optional
from bson import ObjectId
from pydantic import BaseModel, Field

from backend.models.user.folder_entry import FolderEntry


class UserFolder(BaseModel):
    id: Optional[ObjectId] = Field(default_factory=ObjectId)
    entries: Optional[List[FolderEntry]] = []

    class Config:
        arbitrary_types_allowed = True 

    def to_dict(self):
        return {
            "id": str(self.id) if self.id else None,
            "entries": [entry.model_dump() for entry in self.entries]
        }
