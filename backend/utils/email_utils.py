from pydantic import EmailStr, ValidationError

def isEmail(email: str) -> bool:
    try:
        EmailStr(email)
        return True
    except ValidationError:
        return False

