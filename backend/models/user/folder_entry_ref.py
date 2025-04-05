from bson import ObjectId
from pydantic import Field

from .base_model import BaseModel


class FolderEntryRef(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
