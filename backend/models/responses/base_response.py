from pydantic import BaseModel, Field

from models.responses.signature_response import SignatureResponse


class BaseResponse(BaseModel):
    status: str = "success"
    data: BaseModel
    signature: SignatureResponse = Field(default_factory=SignatureResponse)
