from fastapi import HTTPException
from pydantic import BaseModel, EmailStr, ValidationError


class EmailValidator(BaseModel):
    email: EmailStr


def isEmail(email: str) -> str:
    try:
        EmailValidator(email=email)
        return email
    except ValidationError as e:
        raise
