from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .aggregation import aggregate_iteration
from .decision import iteration_valid_for_comparison
from .evaluator import score_job
from .models import BenchmarkConfig
from .report import render_report
from .telemetry import snapshot_from_mapping


def _config_from_record(record: Mapping[str, Any]) -> BenchmarkConfig:
    raw = dict(record.get("config") or {})
    return BenchmarkConfig(
        summary_level=str(raw.get("summary_level") or "moderate"),
        category=str(raw.get("category") or "education"),
        style=str(raw.get("style") or "guide"),
        output_format=str(raw.get("output_format") or "markdown"),
        language=str(raw.get("language") or "spanish"),
        model=str(raw.get("model") or "qwen3:14b"),
    )


def _load_text(path_value: str) -> str:
    if not path_value:
        return ""
    path = Path(path_value)
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def rescore_experiment(
    record: Mapping[str, Any],
    *,
    source_text: str | None = None,
    summary: str | None = None,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    updated = dict(record)
    config = _config_from_record(record)
    summary_text = summary if summary is not None else _load_text(
        str(record.get("summary_path") or "")
    )
    if summary is None and not summary_text:
        summary_text = str(record.get("summary") or "")
    source = source_text if source_text is not None else _load_text(
        str((record.get("source") or {}).get("extracted_path") or "")
    )
    telemetry = snapshot_from_mapping(record.get("telemetry") or {})
    runtime_payload = runtime or (record.get("runtime") or {})
    status, reasons, warnings, lint, quality = score_job(
        source_text=source,
        summary=summary_text,
        config=config,
        document_name=str(record.get("document") or record.get("document_id") or ""),
        telemetry=telemetry,
        error=str(record.get("error") or ""),
        runtime=runtime_payload if runtime_payload else None,
    )
    updated["status"] = status.value
    updated["invalid_reasons"] = reasons
    updated["warnings"] = warnings
    updated["heuristic_lint"] = lint.to_dict()
    updated["quality"] = quality.to_dict()
    updated["summary_characters"] = len(summary_text)
    updated["summary_words"] = len(summary_text.split())
    updated["telemetry"] = telemetry.to_dict()
    return updated


def rescore_iteration_payload(
    payload: Mapping[str, Any],
    *,
    summaries: Mapping[str, str] | None = None,
    sources: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    summaries = summaries or {}
    sources = sources or {}
    experiments = []
    before = (payload.get("runtime") or {}).get("before") or {}
    for record in payload.get("experiments") or []:
        document = str(record.get("document") or record.get("document_id") or "")
        model = str((record.get("config") or {}).get("model") or "")
        runtime = None
        if isinstance(before, dict) and model and isinstance(before.get(model), dict):
            runtime = before.get(model)
        elif isinstance(before, dict) and "requested_context" in before:
            runtime = before
        experiments.append(
            rescore_experiment(
                record,
                source_text=sources.get(document),
                summary=summaries.get(document),
                runtime=runtime,
            )
        )
    updated = dict(payload)
    updated["experiments"] = experiments
    updated["aggregates"] = aggregate_iteration(experiments)
    comparable, reasons = iteration_valid_for_comparison(updated)
    updated["validity"] = {
        "valid_for_comparison": comparable,
        "reasons": reasons,
        "rescored": True,
    }
    updated["report"] = render_report(updated)
    return updated


def rescore_iteration_file(
    source: Path,
    destination: Path | None = None,
) -> dict[str, Any]:
    payload = json.loads(source.read_text(encoding="utf-8"))
    updated = rescore_iteration_payload(payload)
    if destination is not None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(updated, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return updated
