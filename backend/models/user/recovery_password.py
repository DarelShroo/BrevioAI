from pydantic import BaseModel

class RecoveryPassword(BaseModel):
    identity: str