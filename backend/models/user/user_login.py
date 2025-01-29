from pydantic import BaseModel


class UserLogin(BaseModel):
    identity: str
    password: str