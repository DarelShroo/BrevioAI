from fastapi import Form, HTTPException, Query

from core.brevio.enums.language import LanguageType


def parse_language_enum(language: str) -> LanguageType:
    try:
        print("lenguaje", language)
        return LanguageType[language.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid language: {language}")


def language_from_query(language: str = Query(...)) -> LanguageType:
    return parse_language_enum(language)


def language_from_form(language: str = Form(...)) -> LanguageType:
    return parse_language_enum(language)
