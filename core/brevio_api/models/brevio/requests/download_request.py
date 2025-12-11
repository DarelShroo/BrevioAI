from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class RenameStrategy(str, Enum):
    KEEP = "keep"
    STRIP_UUID = "strip_uuid"


class DownloadFileItem(BaseModel):
    filename: str = Field(..., description="Original filename on server")
    new_filename: Optional[str] = Field(
        None, description="New filename for the download"
    )


class DownloadRequest(BaseModel):
    folder_id: str = Field(..., description="The ID of the folder to download from")
    include_types: List[str] = Field(
        default_factory=list,
        description="List of extensions to include (e.g. ['pdf', 'md'])",
    )
    files: List[DownloadFileItem] = Field(
        default_factory=list, description="Specific files to include or rename"
    )
    global_rename_strategy: RenameStrategy = Field(
        default=RenameStrategy.KEEP,
        description="Strategy for renaming files not explicitly renamed",
    )
    download_all: bool = Field(
        default=True,
        description="If true, download all files matching types. If false, only download listed files.",
    )
