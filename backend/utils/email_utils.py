from pydantic import BaseModel, EmailStr, ValidationError

class EmailValidator(BaseModel):
    email: EmailStr

def isEmail(email: str) -> bool:
    try:
        EmailValidator(email=email)
        return True
    except ValidationError:
        return False

