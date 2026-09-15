from __future__ import annotations

from .claims import extract_claims
from .decision import compare_iterations
from .job_validation import classify_job
from .lint import evaluate_lint
from .models import BenchmarkConfig, HeuristicLint, JobStatus, QualityVector, TelemetrySnapshot
from .quality import evaluate_quality


def score_job(
    *,
    source_text: str,
    summary: str,
    config: BenchmarkConfig,
    document_name: str = "",
    telemetry: TelemetrySnapshot | None = None,
    error: str = "",
    runtime: dict | None = None,
) -> tuple[JobStatus, list[str], list[str], HeuristicLint, QualityVector]:
    snapshot = telemetry or TelemetrySnapshot()
    lint = evaluate_lint(
        source_text=source_text,
        summary=summary,
        config=config,
        telemetry=snapshot,
    )
    status, reasons, warnings, lint = classify_job(
        summary=summary,
        error=error,
        config=config,
        telemetry=snapshot,
        runtime=runtime,
        lint=lint,
        source_text=source_text,
    )
    quality = evaluate_quality(
        source_text=source_text,
        summary=summary,
        config=config,
        document_name=document_name or "unknown",
        telemetry=snapshot,
        lint=lint,
        status=status.value,
    )
    return status, reasons, warnings, lint, quality


# Back-compat names. evaluate_summary no longer returns a cosmetic overall
# quality score; it returns the lint+quality bundle used by the runner.


def evaluate_summary(
    *,
    source_text: str,
    summary: str,
    config: BenchmarkConfig,
    telemetry: TelemetrySnapshot | None = None,
    outline: list[str] | None = None,
    document_name: str = "",
    error: str = "",
    runtime: dict | None = None,
) -> QualityVector:
    del outline
    _, _, _, _, quality = score_job(
        source_text=source_text,
        summary=summary,
        config=config,
        document_name=document_name,
        telemetry=telemetry,
        error=error,
        runtime=runtime,
    )
    return quality


def compare_level_progression(records: list[dict]) -> dict:
    grouped: dict[tuple, dict] = {}
    for rec in records:
        cfg = rec.get("config") or {}
        key = (
            str(rec.get("document") or ""),
            str(cfg.get("model") or ""),
            str(cfg.get("category") or ""),
            str(cfg.get("style") or ""),
            str(cfg.get("language") or ""),
        )
        grouped.setdefault(key, {})[str(cfg.get("summary_level") or "")] = rec
    reports = []
    for key, by_level in grouped.items():
        needed = ("very_concise", "moderate", "very_detailed")
        if not all(level in by_level for level in needed):
            continue
        words = [by_level[level]["summary_words"] for level in needed]
        coverage = [
            ((by_level[level].get("quality") or {}).get("coverage"))
            for level in needed
        ]
        reports.append(
            {
                "group": {
                    "document": key[0],
                    "model": key[1],
                    "category": key[2],
                    "style": key[3],
                    "language": key[4],
                },
                "words": dict(zip(needed, words)),
                "coverage": dict(zip(needed, coverage)),
                "strict_progression": (
                    words[0] < words[1] < words[2]
                    and coverage[0] is not None
                    and coverage[2] is not None
                    and coverage[0] <= coverage[2]
                ),
            }
        )
    return {
        "groups": reports,
        "ok": all(item["strict_progression"] for item in reports) if reports else False,
    }


__all__ = [
    "compare_iterations",
    "compare_level_progression",
    "evaluate_lint",
    "evaluate_quality",
    "evaluate_summary",
    "extract_claims",
    "score_job",
]
