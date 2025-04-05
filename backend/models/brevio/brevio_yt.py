from pydantic import BaseModel


class BrevioYT(BaseModel):
    url: str
    language: str
