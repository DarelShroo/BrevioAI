from typing import List

from pydantic import BaseModel


class EntryRef(BaseModel):
    entries_refs: List[str]
