from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from bson import ObjectId

class User(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    username: str
    email: EmailStr
    password: str
    otp: Optional[int] = None
    exp: Optional[int] = None

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
