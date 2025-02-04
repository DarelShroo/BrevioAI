from pydantic import BaseModel


class LoginUser(BaseModel):
    identity: str
    password: str