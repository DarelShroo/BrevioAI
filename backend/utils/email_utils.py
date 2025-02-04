from pydantic import EmailStr, ValidationError

def isEmail(email: str) -> bool:
    try:
        isValidEmail: EmailStr = email
        return True
    except ValidationError:
        return False

