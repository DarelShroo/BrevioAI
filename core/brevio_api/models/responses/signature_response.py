from pydantic import BaseModel


class SignatureResponse(BaseModel):
    brand: str = "Brevio"
    version: str = "v1.0"
    contact: str = "support@brevio.com"
