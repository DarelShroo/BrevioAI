from pydantic import BaseModel

from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.source_type import SourceType
from core.brevio.enums.summary_level import SummaryLevel
from core.shared.enums.model import ModelType


class HistoryTokenModel(BaseModel):
    model: ModelType = ModelType.GPT_4
    language_input: LanguageType = LanguageType.ENGLISH
    language_output: LanguageType = LanguageType.ENGLISH
    category: str = ""
    style: str = ""
    output_format: OutputFormatType = OutputFormatType.MARKDOWN
    source_type: SourceType = SourceType.TEXT
    summary_level: SummaryLevel = SummaryLevel.VERY_CONCISE
    num_tokens_file: int = 0
    num_chars_file: int = 0
    num_tokens_summary_input: int = 0
    num_tokens_summary_output: int = 0
    num_tokens_postprocess_output: int = 0
    num_tokens_postprocess_input: int = 0
    num_total_tokens: int = 0
    num_tokens_summary_predict_input: int = 0
    num_tokens_summary_predict_output: int = 0
    num_tokens_postprocess_predict_input: int = 0
    num_tokens_postprocess_predict_output: int = 0
    num_total_tokens_predict: int = 0
    input_factor: float = 0.0
    output_factor_map_summary: float = 0.0
