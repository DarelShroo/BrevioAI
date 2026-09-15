from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Iterable, Mapping, Sequence

from .models import QUALITY_ELIGIBLE, JobStatus

QUALITY_FIELDS = (
    "fidelity",
    "coverage",
    "completeness",
    "hallucination",
    "contradiction",
    "coherence",
    "utility",
    "language",
    "instruction_adherence",
    "quality_score",
)


def _floats(values: Iterable[Any]) -> list[float]:
    out: list[float] = []
    for value in values:
        if value is None or value == "":
            continue
        try:
            out.append(float(value))
        except (TypeError, ValueError):
            continue
    return out


def percentile(values: Sequence[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    rank = (len(ordered) - 1) * (p / 100.0)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return round(ordered[low], 2)
    weight = rank - low
    return round(ordered[low] * (1.0 - weight) + ordered[high] * weight, 2)


def summarize(values: Iterable[Any]) -> dict[str, Any]:
    items = _floats(values)
    if not items:
        return {
            "n": 0,
            "mean": None,
            "median": None,
            "p10": None,
            "p25": None,
            "p75": None,
            "p90": None,
            "min": None,
            "max": None,
            "std": None,
        }
    mean = sum(items) / len(items)
    var = sum((item - mean) ** 2 for item in items) / len(items)
    return {
        "n": len(items),
        "mean": round(mean, 2),
        "median": percentile(items, 50),
        "p10": percentile(items, 10),
        "p25": percentile(items, 25),
        "p75": percentile(items, 75),
        "p90": percentile(items, 90),
        "min": round(min(items), 2),
        "max": round(max(items), 2),
        "std": round(math.sqrt(var), 2),
    }


def _quality_rows(records: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    rows = []
    for record in records:
        status = str(record.get("status") or "")
        if status and status not in {item.value for item in QUALITY_ELIGIBLE}:
            continue
        if record.get("error") and status != JobStatus.VALID.value:
            continue
        quality = record.get("quality") or {}
        if quality.get("quality_score") is None and quality.get("fidelity") is None:
            continue
        rows.append(record)
    return rows


def _group(records: Sequence[Mapping[str, Any]], key: str) -> dict[str, list[Mapping[str, Any]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        config = record.get("config") or {}
        if key == "document":
            label = str(record.get("document_id") or record.get("document") or "")
        elif key == "model":
            label = str(config.get("model") or "")
        elif key == "language":
            label = str(config.get("language") or "")
        elif key == "level":
            label = str(config.get("summary_level") or "")
        elif key == "category":
            label = str(config.get("category") or "")
        elif key == "style":
            label = str(config.get("style") or "")
        else:
            label = ""
        grouped[label].append(record)
    return dict(grouped)


def _quality_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    payload = {}
    for field in QUALITY_FIELDS:
        payload[field] = summarize(
            (row.get("quality") or {}).get(field) for row in records
        )
    return payload


def _cost_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    tokens = []
    seconds = []
    retries = []
    costs = []
    for record in records:
        tele = record.get("telemetry") or {}
        if tele.get("telemetry_status") != "present":
            continue
        total = tele.get("total_tokens")
        if total is None:
            parts = [
                tele.get("total_tokens_summary_input"),
                tele.get("total_tokens_summary_output"),
                tele.get("total_tokens_postprocess_input"),
                tele.get("total_tokens_postprocess_output"),
            ]
            if all(item is not None for item in parts):
                total = sum(int(item) for item in parts)
        if total is not None:
            tokens.append(total)
        if tele.get("total_time") is not None:
            seconds.append(tele.get("total_time"))
        if tele.get("retry_requests") is not None:
            retries.append(tele.get("retry_requests"))
        if tele.get("estimated_provider_cost") is not None:
            costs.append(tele.get("estimated_provider_cost"))
    return {
        "tokens": summarize(tokens),
        "seconds": summarize(seconds),
        "retries": summarize(retries),
        "provider_cost": summarize(costs) if costs else {
            "n": 0,
            "mean": None,
            "median": None,
            "p10": None,
            "p25": None,
            "p75": None,
            "p90": None,
            "min": None,
            "max": None,
            "std": None,
        },
        "jobs_with_telemetry": len(tokens),
        "jobs_missing_telemetry": sum(
            1
            for record in records
            if (record.get("telemetry") or {}).get("telemetry_status") != "present"
        ),
    }


def aggregate_iteration(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    all_rows = list(records)
    valid = [
        row
        for row in all_rows
        if str(row.get("status") or "") == JobStatus.VALID.value
    ]
    invalid = [
        row
        for row in all_rows
        if str(row.get("status") or "") not in {"", JobStatus.VALID.value, JobStatus.FAILED.value, JobStatus.TIMEOUT.value}
    ]
    failed = [
        row
        for row in all_rows
        if str(row.get("status") or "") in {JobStatus.FAILED.value, JobStatus.TIMEOUT.value}
        or (row.get("error") and str(row.get("status")) != JobStatus.VALID.value)
    ]
    counts = {
        "jobs": len(all_rows),
        "valid_jobs": len(valid),
        "invalid_jobs": len(invalid),
        "failed_jobs": len(failed),
        "chatbot_artifacts": sum(
            1 for row in all_rows if row.get("status") == JobStatus.CHATBOT_OUTPUT.value
        ),
        "language_mismatch": sum(
            1 for row in all_rows if row.get("status") == JobStatus.LANGUAGE_MISMATCH.value
        ),
        "truncations": sum(
            1 for row in all_rows if row.get("status") == JobStatus.TRUNCATED.value
        ),
        "runtime_invalid": sum(
            1 for row in all_rows if row.get("status") == JobStatus.INVALID_RUNTIME.value
        ),
        "telemetry_missing": sum(
            1
            for row in all_rows
            if (row.get("telemetry") or {}).get("telemetry_status") != "present"
        ),
    }
    by_document_scores: list[float] = []
    per_document: dict[str, Any] = {}
    for doc, rows in _group(valid, "document").items():
        summary = _quality_summary(rows)
        per_document[doc] = {
            "n": len(rows),
            "quality": summary,
            "cost": _cost_summary(rows),
        }
        mean_score = (summary.get("quality_score") or {}).get("mean")
        if mean_score is not None:
            by_document_scores.append(mean_score)
    corpus_quality = _quality_summary(valid)
    if by_document_scores:
        corpus_quality["document_equal_weight_quality_score"] = summarize(
            by_document_scores
        )
    strata = {}
    for key in ("model", "language", "level", "category", "style"):
        strata[key] = {
            label: {"n": len(rows), "quality": _quality_summary(rows)}
            for label, rows in _group(valid, key).items()
        }
    return {
        "counts": counts,
        "quality": corpus_quality,
        "cost": _cost_summary(valid),
        "per_document": per_document,
        "per_model": strata["model"],
        "per_language": strata["language"],
        "per_level": strata["level"],
        "per_category": strata["category"],
        "per_style": strata["style"],
    }
