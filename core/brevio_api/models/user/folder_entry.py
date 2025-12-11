from typing import List, Optional

from bson import ObjectId
from pydantic import Field

from ....shared.models.user.base_model import BaseModel, SerializedObjectId
from ....shared.models.user.data_result import DataResult
from ..brevio.file_metadata import FileMetadata


class FolderEntry(BaseModel):
    id: SerializedObjectId = Field(default_factory=ObjectId, alias="_id")
    user_id: SerializedObjectId = Field(default_factory=ObjectId, alias="user_id")
    name: str = Field(default="", strict=True, max_length=100)
    results: List[DataResult] = Field(default_factory=list)
    files_metadata: Optional[List[FileMetadata]] = Field(
        default=None, description="Metadata of files in this entry"
    )
