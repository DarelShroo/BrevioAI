from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


BENCHMARK_VERSION = "2.0.0"
SCORER_VERSION = "2.0.0"
JUDGE_VERSION = "2.0.0-optional"
DEFAULT_REQUESTED_CONTEXT = 16_384


class JobStatus(str, Enum):
    VALID = "VALID"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    INVALID_ARTIFACT = "INVALID_ARTIFACT"
    INVALID_RUNTIME = "INVALID_RUNTIME"
    INVALID_TELEMETRY = "INVALID_TELEMETRY"
    TRUNCATED = "TRUNCATED"
    CHATBOT_OUTPUT = "CHATBOT_OUTPUT"
    LANGUAGE_MISMATCH = "LANGUAGE_MISMATCH"
    INSUFFICIENT_OUTPUT = "INSUFFICIENT_OUTPUT"


QUALITY_ELIGIBLE = frozenset({JobStatus.VALID, JobStatus.TRUNCATED})


@dataclass(frozen=True)
class BenchmarkConfig:
    summary_level: str = "moderate"
    category: str = "education"
    style: str = "guide"
    output_format: str = "markdown"
    language: str = "spanish"
    model: str = "qwen3:14b"

    def to_form(self) -> dict[str, str]:
        return {
            "language": self.language,
            "model": self.model,
            "category": self.category,
            "style": self.style,
            "format": self.output_format,
            "summary_level": self.summary_level,
        }

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    def cell_key(self, document_id: str) -> tuple[str, ...]:
        return (
            document_id,
            self.model,
            self.language,
            self.summary_level,
            self.category,
            self.style,
            self.output_format,
        )

    def slug(self) -> str:
        model = self.model.replace(":", "-").replace(".", "-")
        return (
            f"{self.summary_level}-{self.category}-{self.style}-"
            f"{self.language}-{model}-{self.output_format}"
        )


DEFAULT_BENCHMARK_MODELS: tuple[str, ...] = ("qwen3:14b",)

# Comparable grid: every document gets the same cells (language may be
# resolved to the document native language when the CLI passes "auto").
COMPARISON_MATRIX: tuple[BenchmarkConfig, ...] = (
    BenchmarkConfig("very_concise", "education", "guide"),
    BenchmarkConfig("moderate", "education", "guide"),
    BenchmarkConfig("very_detailed", "education", "guide"),
)

# Legacy per-book slices. Not used for comparison. Kept so old JSON can
# still be described; configs_for_document no longer consults this.
DOCUMENT_MATRIX: tuple[tuple[str, tuple[BenchmarkConfig, ...]], ...] = ()
DEFAULT_MATRIX: tuple[BenchmarkConfig, ...] = COMPARISON_MATRIX


@dataclass(frozen=True)
class BenchmarkPaths:
    root: Path

    @property
    def summaries(self) -> Path:
        return self.root / "summaries"

    @property
    def sources(self) -> Path:
        return self.root / "sources"

    @property
    def results(self) -> Path:
        return self.root / "results"

    @property
    def iterations(self) -> Path:
        return self.root / "iterations"

    @property
    def audit(self) -> Path:
        return self.root / "audit"

    def ensure(self) -> None:
        for path in (
            self.summaries,
            self.sources,
            self.results,
            self.iterations,
            self.audit,
        ):
            path.mkdir(parents=True, exist_ok=True)


@dataclass
class TelemetrySnapshot:
    folder_id: str = ""
    telemetry_status: str = "missing"
    model: str | None = None
    language_input: str | None = None
    language_output: str | None = None
    category: str | None = None
    style: str | None = None
    summary_level: str | None = None
    num_tokens_file: int | None = None
    num_chars_file: int | None = None
    number_of_chunks: int | None = None
    route: str | None = None
    map_requests: int | None = None
    reduce_requests: int | None = None
    format_requests: int | None = None
    direct_requests: int | None = None
    api_request_count: int | None = None
    retry_requests: int | None = None
    failed_requests: int | None = None
    connectivity_probes: int | None = None
    truncation_detected: bool | None = None
    total_tokens_summary_input: int | None = None
    total_tokens_summary_output: int | None = None
    total_tokens_postprocess_input: int | None = None
    total_tokens_postprocess_output: int | None = None
    total_time: float | None = None
    output_min_tokens: int | None = None
    output_target_tokens: int | None = None
    output_max_tokens: int | None = None
    pipeline_status: str | None = None
    pipeline_phase: str | None = None
    phase_token_totals: dict[str, dict[str, int]] = field(default_factory=dict)
    calls_by_type: dict[str, int] = field(default_factory=dict)
    wasted_retry_tokens: int | None = None
    retry_tokens: int | None = None
    physical_http_requests: int | None = None
    estimated_provider_cost: float | None = None
    cost_currency: str | None = None
    pricing_version: str | None = None
    phase_prompt_hashes: dict[str, list[str]] = field(default_factory=dict)
    token_accounting: str = "unknown"
    history_tokens_per_call: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def total_tokens(self) -> int | None:
        parts = [
            self.total_tokens_summary_input,
            self.total_tokens_summary_output,
            self.total_tokens_postprocess_input,
            self.total_tokens_postprocess_output,
        ]
        if any(item is None for item in parts):
            return None
        return int(sum(int(item or 0) for item in parts))


@dataclass
class QualityVector:
    fidelity: float | None = None
    coverage: float | None = None
    completeness: float | None = None
    hallucination: float | None = None
    contradiction: float | None = None
    coherence: float | None = None
    utility: float | None = None
    language: float | None = None
    instruction_adherence: float | None = None
    quality_score: float | None = None
    gold_coverage: str = "unavailable"
    notes: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HeuristicLint:
    language_label: str = ""
    language_score: float | None = None
    chatbot_score: float = 0.0
    copy_ratio: float | None = None
    truncation_signals: list[str] = field(default_factory=list)
    first_person: bool = False
    markdown_headings: int = 0
    summary_words: int = 0
    source_words: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExperimentRecord:
    iteration_id: str
    document: str
    document_path: str
    document_id: str = ""
    config: dict[str, str] = field(default_factory=dict)
    folder_entry_id: str = ""
    task_id: str = ""
    summary_path: str = ""
    summary_characters: int = 0
    summary_words: int = 0
    wall_seconds: float = 0.0
    source: dict[str, Any] = field(default_factory=dict)
    telemetry: dict[str, Any] = field(default_factory=dict)
    quality: dict[str, Any] = field(default_factory=dict)
    heuristic_lint: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    status: str = JobStatus.FAILED.value
    invalid_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    fingerprint: str = ""
    cell_key: list[str] = field(default_factory=list)
    judge: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def record_from_mapping(item: dict[str, Any]) -> ExperimentRecord:
    known = set(ExperimentRecord.__dataclass_fields__)
    payload = {key: value for key, value in item.items() if key in known}
    return ExperimentRecord(**payload)
