from pydantic import BaseModel, EmailStr


class RegisterUser(BaseModel):
    username: str
    email: EmailStr
    password: str

    def to_dict(self):
        return {
            "username": self.username,
            "email": self.email,
            "password": self.password
        }