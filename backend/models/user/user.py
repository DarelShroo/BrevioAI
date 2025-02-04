from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from bson import ObjectId

class User(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")  # _id will be treated as id
    username: str
    email: EmailStr
    password: str

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}  # Automatically convert ObjectId to string
