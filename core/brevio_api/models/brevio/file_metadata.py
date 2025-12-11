from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class FileMetadata(BaseModel):
    name: str = Field(..., description="Name of the file or directory")
    path: str = Field(..., description="Relative path from the user folder root")
    type: str = Field(..., description="File extension or 'directory'")
    size: int = Field(..., description="Size in bytes")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    children: Optional[List[FileMetadata]] = Field(
        default=None, description="List of children if this is a directory"
    )
