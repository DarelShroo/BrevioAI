from pydantic import BaseModel, EmailStr
class RecoveryPasswordOtp(BaseModel):
    email: EmailStr
    password: str
    otp: int

