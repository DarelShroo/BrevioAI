from typing import List, Union

from bson import ObjectId
from pydantic import BaseModel, Field

from brevio.models.response_model import FolderResponse
from models.responses.base_response import BaseResponse
from models.user.folder_entry import FolderEntry
from models.user.folder_entry_ref import FolderEntryRef


class LoginResponse(BaseModel):
    access_token: str


class LoginDataResponse(BaseResponse):
    data: LoginResponse


class RegisterResponse(BaseModel):
    folder: FolderResponse
    token: str


class RegisterDataResponse(BaseResponse):
    data: RegisterResponse


class PasswordRecoveryResponse(BaseModel):
    message: str


class PasswordRecoveryDataResponse(BaseResponse):
    data: PasswordRecoveryResponse


class UserEntriesRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    next_entries: int = Field(..., description="Number of next entries to retrieve")


class UserEntriesResponse(BaseModel):
    entries_ref: List[FolderEntryRef] = Field(
        ..., description="List of entry references"
    )


class EntriesRequest(BaseModel):
    entries_ref: List[FolderEntryRef] = Field(
        ..., description="List of entry references to process"
    )


class EntriesResponse(BaseModel):
    entries: List[FolderEntry] = Field(
        ..., description="List of processed entries with details"
    )
