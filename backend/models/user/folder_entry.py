from typing import List, Optional

from bson import ObjectId
from pydantic import Field

from .base_model import BaseModel
from .data_result import DataResult


class FolderEntry(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    user_id: ObjectId
    name: str = ""
    results: List[DataResult] = Field(default_factory=list)
