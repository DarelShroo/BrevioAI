# En brevio_generate_model.py
from pydantic import BaseModel, HttpUrl, FilePath, model_validator
from typing import List, Optional
from backend.brevio.models.prompt_config_model import PromptConfig
from backend.brevio.models.summary_config_model import SummaryConfig

class MediaEntry(BaseModel):
    url: Optional[HttpUrl] = None
    path: Optional[FilePath] = None

    @model_validator(mode='after')
    def validate_media(self) -> 'MediaEntry':
        if not self.url and not self.path:
            raise ValueError("Se requiere 'url' o 'path'")
        return self

class BaseBrevioGenerate(BaseModel):
    summary_config: SummaryConfig
    prompt_config: PromptConfig

class BrevioGenerate(BaseBrevioGenerate):
    data: List[MediaEntry]
