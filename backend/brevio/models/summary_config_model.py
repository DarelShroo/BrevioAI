from dataclasses import dataclass
from backend.brevio.enums.content import ContentType
from backend.brevio.enums.language import LanguageType
from backend.brevio.enums.model import ModelType

@dataclass
class SummaryConfig:
    transcription_path: str
    summary_path: str
    content: ContentType
    language: LanguageType
    model: ModelType
