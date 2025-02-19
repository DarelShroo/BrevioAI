from pydantic import BaseModel
from typing import List

from backend.brevio.enums.model import ModelType

class DurationEntry(BaseModel):
    url: str

class BrevioGenerate(BaseModel):
    data: List[DurationEntry]
    language: str
    model: ModelType
    content: str
