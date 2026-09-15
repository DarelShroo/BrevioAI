from typing import List

from fastapi import HTTPException

from core.brevio_api.models.errors.api_codes import ApiErrorCode


class InvalidFileExtension(HTTPException):
    def __init__(
        self,
        filename: str,
        allowed_extensions: List[str],
        code: ApiErrorCode | str = ApiErrorCode.FILE_FORMAT_NOT_ALLOWED,
    ):
        detail = (
            f"Invalid file extension for file '{filename}'. "
            f"Allowed extensions are: {', '.join(allowed_extensions)}."
        )
        super().__init__(status_code=415, detail=detail)
        self.filename = filename
        self.allowed_extensions = allowed_extensions
        self.code = code.value if isinstance(code, ApiErrorCode) else code
