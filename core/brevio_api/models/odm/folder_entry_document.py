from typing import List

from beanie import Document
from bson import ObjectId
from pydantic import ConfigDict, Field

from core.shared.models.user.data_result import DataResult


class FolderEntryDocument(Document):
    user_id: ObjectId
    name: str = Field(default="", max_length=100)
    results: List[DataResult] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    class Settings:
        name = "entries"
