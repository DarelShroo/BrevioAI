from typing import List, Optional

from pydantic import BaseModel, Field


class FileItem(BaseModel):
    filename: str = Field(..., description="Name of the file")
    path: str = Field(..., description="Relative path from the folder root")
    size: int = Field(..., description="Size in bytes")
    type: str = Field(..., description="File extension")


class FolderContentResponse(BaseModel):
    folder_id: str = Field(..., description="The ID of the folder (entry)")
    files: List[List[FileItem]] = Field(
        default_factory=list, description="List of grouped files in this folder"
    )


class UserFoldersResponse(BaseModel):
    folder_ids: List[str] = Field(
        default_factory=list, description="List of user folder IDs"
    )
