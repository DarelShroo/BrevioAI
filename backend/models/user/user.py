from pydantic import EmailStr

class User:
    username: str
    email: EmailStr
    hashed_password: str
    token: str


