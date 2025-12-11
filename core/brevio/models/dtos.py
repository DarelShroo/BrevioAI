from dataclasses import dataclass
from typing import Any, List, Optional

from core.brevio.enums.language import LanguageType
from core.brevio.models.file_config_model import FileConfig
from core.brevio.models.prompt_config_model import PromptConfig
from core.shared.enums.model import ModelType
from core.shared.models.user.data_result import DataResult


@dataclass
class ChunkProcessingRequest:
    index: int
    chunk: str
    prompt: str
    accumulated_summary: str
    model: ModelType
    language: LanguageType
    retries: int = 0


@dataclass
class PostProcessRequest:
    clean_summary: str
    clean_summary_tokens: int
    model: ModelType
    language: LanguageType


@dataclass
class DocumentProcessingRequest:
    prompt_config: PromptConfig
    file_config: FileConfig
    data_result: Optional[DataResult] = None
