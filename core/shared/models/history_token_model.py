from uuid import uuid4

from pydantic import BaseModel, Field, computed_field

from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.source_type import SourceType
from core.brevio.enums.style import StyleType
from core.brevio.enums.summary_level import SummaryLevel
from core.shared.enums.model import ModelType
from core.shared.models.brevio.history_token_call import HistoryTokenCall


class HistoryTokenModel(BaseModel):
    execution_id: str = Field(default_factory=lambda: str(uuid4()))
    folder_id: str | None = None
    user_id: str | None = None
    model: ModelType = ModelType.GPT_4
    language_input: str = "english"  # detected document/source language
    language_output: str = "english"  # target/output language for the summary
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
    started_at: str | None = None
    # Wall-clock pipeline duration in seconds (e.g. 213.793), not a datetime.
    total_time: float | None = Field(
        default=0.0, description="Pipeline duration in seconds"
    )
    # Completion datetime (local), complementary to total_time.
    completed_at: str | None = Field(
        default=None,
        description="Pipeline completion datetime YYYY-MM-DD HH:MM:SS",
    )
    api_request_count: int = 0
    physical_http_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    retry_requests: int = 0
    rate_limit_waits: int = 0
    rate_limit_wait_seconds: float = 0.0
    provider_429_count: int = 0
    global_cooldown_count: int = 0
    job_request_budget_consumed: int = 0
    job_request_budget_remaining: int = 0
    job_expected_requests: int = 0
    connectivity_probes: int = 0
    provider_requests_by_phase: dict[str, dict[str, int]] = Field(default_factory=dict)
    phase_prompt_hashes: dict[str, list[str]] = Field(default_factory=dict)
    map_requests: int = 0
    reduce_requests: int = 0
    format_requests: int = 0
    direct_requests: int = 0
    route: str = ""
    number_of_chunks: int = 0
    output_min_tokens: int = 0
    output_target_tokens: int = 0
    output_max_tokens: int = 0
    output_hard_limit: int = 0
    pipeline_status: str = ""
    pipeline_phase: str = ""
    truncation_detected: bool = False
    map_output_tokens: int = 0
    map_output_words: int = 0
    reduce_output_tokens: int = 0
    format_output_tokens: int = 0
    final_artifact_tokens: int = 0
    final_artifact_words: int = 0
    chunk_id_representation: str = ""
    quality_verdict: str = ""
    salvage_source: str = ""
    pages_total: int = 0
    pages_extracted: int = 0
    pages_empty: int = 0
    pages_ocr: int = 0
    pages_ocr_failed: int = 0
    pages_dropped: int = 0
    toc_chars_before: int = 0
    toc_chars_after: int = 0
    toc_drop_ratio: float = 0.0
    extraction_kind: str = "generation"
    # Operational / logs.json only — NOT commercial authority (FASE 4: CostRecord).
    estimated_provider_cost: float = 0.0
    cost_currency: str = "USD"
    pricing_version: str = ""
    history_tokens_per_call: list[HistoryTokenCall] = Field(default_factory=list)

    @computed_field  # Calcula el valor dinámicamente
    @property
    def total_total_tokens(self) -> int:
        return (
            self.total_tokens_summary_input
            + self.total_tokens_summary_output
            + self.total_tokens_postprocess_output
            + self.total_tokens_postprocess_input
        )

    @computed_field
    @property
    def total_input_tokens(self) -> int:
        return self.total_tokens_summary_input + self.total_tokens_postprocess_input

    @computed_field
    @property
    def total_output_tokens(self) -> int:
        return self.total_tokens_summary_output + self.total_tokens_postprocess_output

    @computed_field
    @property
    def phase_token_totals(self) -> dict[str, dict[str, int]]:
        totals: dict[str, dict[str, int]] = {}
        for call in self.history_tokens_per_call:
            phase = {
                "summary": "MAP",
                "direct": "DIRECT",
                "reduce": "REDUCE",
                "format": "FORMAT",
            }.get(call.type_call.value, call.type_call.value.upper())
            bucket = totals.setdefault(
                phase,
                {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            )
            bucket["input_tokens"] += call.input_tokens
            bucket["output_tokens"] += call.response_tokens
            bucket["total_tokens"] += call.total_tokens
        return totals


HistoryTokenModel.model_rebuild()
