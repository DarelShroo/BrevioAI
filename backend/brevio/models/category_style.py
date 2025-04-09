from dataclasses import dataclass
from typing import Dict, List

from pydantic import BaseModel


class Style(BaseModel):
    style: str
    source_types: List[str]
