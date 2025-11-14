from pydantic import BaseModel, computed_field

from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.source_type import SourceType
from core.brevio.enums.style import StyleType
from core.brevio.enums.summary_level import SummaryLevel
from core.shared.enums.model import ModelType
from core.shared.models.brevio.history_token_call import HistoryTokenCall


class HistoryTokenModel(BaseModel):
    model: ModelType = ModelType.GPT_4
    language_input: str = "english"
    language_output: str = "english"
    category: str = CategoryType.EDUCATION.value
    style: str = StyleType.EDUCATION_GUIDE.value
    output_format: str = OutputFormatType.MARKDOWN.value
    source_type: str = SourceType.TEXT.value
    summary_level: str = SummaryLevel.CONCISE.value
    num_tokens_file: int = 0
    num_chars_file: int = 0
    total_tokens_summary_input: int = 0
    total_tokens_summary_output: int = 0
    total_tokens_postprocess_output: int = 0
    total_tokens_postprocess_input: int = 0
    total_time: float | None = 0
    history_tokens_per_call: list[HistoryTokenCall] = []

    @computed_field  # Calcula el valor dinámicamente
    def total_total_tokens(self) -> int:
        return (
            self.total_tokens_summary_input
            + self.total_tokens_summary_output
            + self.total_tokens_postprocess_output
            + self.total_tokens_postprocess_input
        )


HistoryTokenModel.model_rebuild()
