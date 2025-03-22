# backend/models/user/folder_entry.py
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId

class FolderEntry(BaseModel):
    id: ObjectId = Field(default=None, alias="_id")
    name: str
    results: list = []

    model_config = ConfigDict(arbitrary_types_allowed=True)