from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CreateLibraryFolderRequest(BaseModel):
    name: str


class RenameLibraryFolderRequest(BaseModel):
    name: str


class PatchFolderEntryRequest(BaseModel):
    name: Optional[str] = None
    library_folder_id: Optional[str] = None


class MoveFolderEntriesRequest(BaseModel):
    entry_ids: List[str] = Field(default_factory=list)
    library_folder_id: Optional[str] = None


class BulkDeleteEntriesRequest(BaseModel):
    entry_ids: List[str] = Field(default_factory=list)


class BulkEntryFailure(BaseModel):
    id: str
    code: str


class BulkEntriesResponse(BaseModel):
    succeeded: List[str]
    failed: List[BulkEntryFailure]


class LibraryFolderView(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    entry_count: int


class ListLibraryFoldersResponse(BaseModel):
    folders: List[LibraryFolderView]
    unfiled_count: int
