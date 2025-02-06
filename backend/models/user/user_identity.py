from pydantic import BaseModel

class UserIdentity(BaseModel):
    identity: str