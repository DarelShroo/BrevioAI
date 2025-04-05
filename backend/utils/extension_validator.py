from os import path
from typing import List, Optional, cast

from fastapi import HTTPException, UploadFile

from models.errors.invalid_file_extension import InvalidFileExtension


def validate_file_extension(
    file: UploadFile, allowed_extensions: List[str]
) -> UploadFile:
    try:
        if file.filename is None:
            raise ValueError("Filename cannot be None")

        filename = cast(str, file.filename)
        _, ext = path.splitext(filename)

        ext = ext[1:].lower() if ext else ""

        if not ext or ext not in allowed_extensions:
            raise InvalidFileExtension(
                filename=filename, allowed_extensions=allowed_extensions
            )

        return file

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidFileExtension:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Error validating file extension: {str(e)}"
        )
