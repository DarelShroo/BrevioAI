from typing import List

from pydantic import BaseModel


class Style(BaseModel):
    style: str
    source_types: List[str]
