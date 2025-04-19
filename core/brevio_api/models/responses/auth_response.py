from typing import List

from bson import ObjectId
from pydantic import Field

from core.brevio.models.response_model import FolderResponse
from core.brevio_api.models.responses.base_response import BaseResponse
from core.brevio_api.models.responses.base_response_model import BaseResponseModel
from core.brevio_api.models.user.folder_entry import FolderEntry


class LoginResponse(BaseResponseModel):
    access_token: str


class LoginDataResponse(BaseResponse):
    data: LoginResponse


class RegisterResponse(BaseResponseModel):
    folder: FolderResponse
    token: str


class RegisterDataResponse(BaseResponse):
    data: RegisterResponse


class PasswordRecoveryResponse(BaseResponseModel):
    message: str


class PasswordRecoveryDataResponse(BaseResponse):
    data: PasswordRecoveryResponse


class UserEntriesRequest(BaseResponseModel):
    user_id: str = Field(..., description="User ID")
    next_entries: int = Field(..., description="Number of next entries to retrieve")


class EntriesRequest(BaseResponseModel):
    entries_ref: List[ObjectId] = Field(
        ..., description="List of entry references to process"
    )


class EntriesResponse(BaseResponseModel):
    entries: List[FolderEntry] = Field(
        ..., description="List of processed entries with details"
    )
