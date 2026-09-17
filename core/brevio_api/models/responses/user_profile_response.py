from typing import Optional

from pydantic import EmailStr

from core.brevio_api.models.responses.base_response import BaseResponse
from core.brevio_api.models.responses.base_response_model import BaseResponseModel


class UserProfileResponse(BaseResponseModel):
    id: str
    username: str
    email: EmailStr
    user_credit: float
    folder_id: Optional[str] = None
    plan_id: str = "free"
    plan_name: str = "Free"
    plan_version: str = "1"
    entitlements: Optional[dict] = None


class UserProfileDataResponse(BaseResponse):
    data: UserProfileResponse
