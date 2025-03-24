# backend/models/user/folder_entry.py
from pydantic import Field, ConfigDict
from bson import ObjectId
from .base_model import BaseModel

class FolderEntry(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    name: str = ""
    results: list = []
