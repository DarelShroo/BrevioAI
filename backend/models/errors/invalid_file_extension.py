from fastapi import HTTPException
from typing import List

class InvalidFileExtension(HTTPException):
    def __init__(self, filename: str, allowed_extensions: List[str]):
        detail = f"Invalid file extension for file '{filename}'. Allowed extensions are: {', '.join(allowed_extensions)}."
        super().__init__(status_code=400, detail=detail)
        self.filename = filename
        self.allowed_extensions = allowed_extensions