from os import path
from typing import List
from fastapi import HTTPException, UploadFile
from backend.models.errors.invalid_file_extension import InvalidFileExtension

def validate_file_extension(file: UploadFile, allowed_extensions: List[str]):
    try:
        filename, ext = path.splitext(file.filename)
        ext = ext[1:].lower()

        if ext not in allowed_extensions:
            raise InvalidFileExtension(filename=file.filename, allowed_extensions=allowed_extensions)
        
        return file

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error validating file extension: {str(e)}"
        )
