# brevio_generate.py

from pydantic import BaseModel, field_validator, HttpUrl, FilePath
from typing import List, Optional

from backend.brevio.enums.content import ContentType
from backend.brevio.enums.language import LanguageType
from backend.brevio.enums.model import ModelType

class MediaEntry(BaseModel):
    url: Optional[HttpUrl] = None
    path: Optional[FilePath] = None

class BaseBrevioGenerate(BaseModel):
    language: LanguageType
    model: ModelType
    content: ContentType

    @field_validator('language', 'model', 'content', mode='before')
    def convert_enum(cls, value, info):
        enum_type = cls.model_fields[info.field_name].annotation

        if isinstance(value, str):
            try:
                return enum_type[value.upper()]
            except KeyError:
                raise ValueError(f"Invalid {info.field_name}: {value}")
        
        return value

class BrevioGenerate(BaseBrevioGenerate):
    data: List[MediaEntry]

class BrevioGenerateContent(BaseBrevioGenerate):
    pass
