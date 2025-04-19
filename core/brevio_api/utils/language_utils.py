from fastapi import Form, HTTPException

from core.brevio.enums.language import LanguageType


def parse_language_type(language: str = Form(...)) -> LanguageType:
    try:
        return LanguageType[language.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid language: {language}")
