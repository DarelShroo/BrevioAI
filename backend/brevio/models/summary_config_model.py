from pydantic import BaseModel, field_validator
from typing import Optional
from pathlib import Path
from backend.brevio.enums.content import ContentType
from backend.brevio.enums.language import LanguageType
from backend.brevio.enums.model import ModelType

class SummaryConfig(BaseModel):
    transcription_path: Optional[str] = None
    pdf_path: Optional[str] = None
    docx_path: Optional[str] = None
    summary_path: str
    content: ContentType
    language: LanguageType
    model: ModelType

    @field_validator('transcription_path', 'pdf_path', 'docx_path', 'summary_path', mode='before')
    def convert_path_to_string(cls, value, info):
        if isinstance(value, Path):
            return str(value)
        return value

    @field_validator('content', 'language', 'model', mode='before')
    def convert_enum(cls, value, info):
        enum_type = cls.model_fields[info.field_name].annotation
        if isinstance(value, str):
            try:
                return enum_type[value.upper()]
            except KeyError:
                raise ValueError(f"Invalid {info.field_name}: {value}")
        return value