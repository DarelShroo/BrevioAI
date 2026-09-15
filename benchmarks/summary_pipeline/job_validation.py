from __future__ import annotations

from .lint import chatbot_signals, evaluate_lint, requested_language_name
from .models import (
    BenchmarkConfig,
    HeuristicLint,
    JobStatus,
    TelemetrySnapshot,
)

MIN_SUMMARY_WORDS = 40


def classify_job(
    *,
    summary: str,
    error: str,
    config: BenchmarkConfig,
    telemetry: TelemetrySnapshot,
    runtime: dict | None = None,
    lint: HeuristicLint | None = None,
    source_text: str = "",
) -> tuple[JobStatus, list[str], list[str], HeuristicLint]:
    reasons: list[str] = []
    warnings: list[str] = []
    lint = lint or evaluate_lint(
        source_text=source_text,
        summary=summary,
        config=config,
        telemetry=telemetry,
    )
    error_text = (error or "").strip()
    if error_text:
        lowered = error_text.lower()
        if "timeout" in lowered or "did not finish" in lowered:
            return JobStatus.TIMEOUT, [error_text], warnings, lint
        return JobStatus.FAILED, [error_text], warnings, lint

    if not (summary or "").strip():
        reasons.append("insufficient output: empty artifact")
        return JobStatus.INSUFFICIENT_OUTPUT, reasons, warnings, lint

    chatbot = chatbot_signals(summary)
    if len(chatbot) >= 2 or lint.chatbot_score >= 50:
        reasons.extend(f"chatbot:{item}" for item in chatbot[:6])
        return JobStatus.CHATBOT_OUTPUT, reasons, warnings, lint

    if lint.summary_words < MIN_SUMMARY_WORDS:
        reasons.append(
            f"insufficient output: words={lint.summary_words} min={MIN_SUMMARY_WORDS}"
        )
        return JobStatus.INSUFFICIENT_OUTPUT, reasons, warnings, lint

    runtime = runtime or {}
    requested = runtime.get("requested_context")
    effective = runtime.get("effective_loaded_context_length")
    if requested is not None and effective is not None:
        try:
            if int(effective) != int(requested):
                reasons.append(
                    f"requested_context={requested} effective_context={effective}"
                )
                return JobStatus.INVALID_RUNTIME, reasons, warnings, lint
        except (TypeError, ValueError):
            warnings.append("runtime context not comparable")

    if telemetry.telemetry_status != "present":
        warnings.append("telemetry_missing")

    if lint.truncation_signals:
        reasons.extend(lint.truncation_signals)
        return JobStatus.TRUNCATED, reasons, warnings, lint

    requested_lang = requested_language_name(config.language)
    if (
        lint.language_score is not None
        and lint.language_score < 50
        and lint.language_label not in {"und", requested_lang}
    ):
        reasons.append(
            f"language mismatch detected={lint.language_label} requested={requested_lang}"
        )
        return JobStatus.LANGUAGE_MISMATCH, reasons, warnings, lint

    if lint.copy_ratio is not None and lint.copy_ratio >= 0.80:
        warnings.append(f"copy_ratio={lint.copy_ratio}")
    if telemetry.telemetry_status != "present":
        reasons.append("telemetry_status=missing")
        return JobStatus.INVALID_TELEMETRY, reasons, warnings, lint
    return JobStatus.VALID, reasons, warnings, lint
