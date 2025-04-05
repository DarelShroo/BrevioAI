from typing import List, Optional

from bson import ObjectId
from pydantic import Field

from .base_model import BaseModel
from .folder_entry_ref import FolderEntryRef


class UserFolder(BaseModel):
    id: Optional[ObjectId] = Field(default_factory=ObjectId, alias="_id")
    entries: List[FolderEntryRef] = Field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id) if self.id else None,
            "entries": [entry.model_dump() for entry in self.entries],
        }
