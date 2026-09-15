from __future__ import annotations

from typing import Any, Mapping, Sequence

from .aggregation import QUALITY_FIELDS
from .models import JobStatus

CRITICAL_DROP = 5.0
HALLUCINATION_DROP = 3.0
MIN_DOCS_FOR_KEEP = 3


def cell_set(records: Sequence[Mapping[str, Any]]) -> set[str]:
    cells: set[str] = set()
    for record in records:
        key = record.get("cell_key")
        if isinstance(key, (list, tuple)) and key:
            cells.add("|".join(str(item) for item in key))
            continue
        config = record.get("config") or {}
        cells.add(
            "|".join(
                [
                    str(record.get("document_id") or record.get("document") or ""),
                    str(config.get("model") or ""),
                    str(config.get("language") or ""),
                    str(config.get("summary_level") or ""),
                    str(config.get("category") or ""),
                    str(config.get("style") or ""),
                    str(config.get("output_format") or ""),
                ]
            )
        )
    return cells


def iterations_comparable(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> tuple[bool, str]:
    before_meta = before.get("provenance") or {}
    after_meta = after.get("provenance") or {}
    before_scorer = before_meta.get("scorer_version") or before.get("scorer_version")
    after_scorer = after_meta.get("scorer_version") or after.get("scorer_version")
    if before_scorer and after_scorer and before_scorer != after_scorer:
        return False, "scorer_version mismatch"
    before_judge = before_meta.get("judge_version") or before.get("judge_version")
    after_judge = after_meta.get("judge_version") or after.get("judge_version")
    if before_judge and after_judge and before_judge != after_judge:
        return False, "judge_version mismatch"
    if before_meta.get("dataset_sha") and after_meta.get("dataset_sha"):
        if before_meta["dataset_sha"] != after_meta["dataset_sha"]:
            return False, "dataset_sha mismatch"
    if before_meta.get("matrix_hash") and after_meta.get("matrix_hash"):
        if before_meta["matrix_hash"] != after_meta["matrix_hash"]:
            return False, "matrix_hash mismatch"
    before_cells = cell_set(before.get("experiments") or [])
    after_cells = cell_set(after.get("experiments") or [])
    if before_cells != after_cells:
        return False, "experiment cell sets differ"
    return True, "ok"


def _quality_value(quality: Mapping[str, Any], field: str) -> float | None:
    aliases = {
        "quality_score": ("quality_score", "overall"),
        "hallucination": ("hallucination", "hallucinations"),
        "contradiction": ("contradiction", "contradictions"),
    }
    for key in aliases.get(field, (field,)):
        value = quality.get(key)
        if isinstance(value, Mapping):
            value = value.get("mean")
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _dim_means(payload: Mapping[str, Any]) -> dict[str, float | None]:
    aggregates = payload.get("aggregates") or {}
    quality = aggregates.get("quality") or {}
    out: dict[str, float | None] = {}
    for field in QUALITY_FIELDS:
        value = _quality_value(quality, field)
        if value is None:
            value = _quality_value(aggregates, field)
        if value is None:
            samples = [
                _quality_value(row.get("quality") or {}, field)
                for row in payload.get("experiments") or []
            ]
            samples = [item for item in samples if item is not None]
            value = (sum(samples) / len(samples)) if samples else None
        out[field] = None if value is None else round(value, 2)
    return out


def _count(payload: Mapping[str, Any], name: str) -> int:
    counts = (payload.get("aggregates") or {}).get("counts") or {}
    if name in counts:
        return int(counts.get(name) or 0)
    status_map = {
        "chatbot_artifacts": JobStatus.CHATBOT_OUTPUT.value,
        "language_mismatch": JobStatus.LANGUAGE_MISMATCH.value,
        "truncations": JobStatus.TRUNCATED.value,
        "runtime_invalid": JobStatus.INVALID_RUNTIME.value,
        "failed_jobs": JobStatus.FAILED.value,
        "invalid_jobs": None,
    }
    experiments = payload.get("experiments") or []
    if name == "invalid_jobs":
        return sum(
            1
            for row in experiments
            if str(row.get("status") or "")
            not in {JobStatus.VALID.value, JobStatus.FAILED.value, JobStatus.TIMEOUT.value, ""}
        )
    wanted = status_map.get(name)
    if name == "truncations":
        return sum(
            1
            for row in experiments
            if row.get("status") == JobStatus.TRUNCATED.value
            or bool((row.get("telemetry") or {}).get("truncation_detected"))
        )
    if wanted:
        return sum(1 for row in experiments if row.get("status") == wanted)
    return 0


def compare_iterations(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> dict[str, Any]:
    comparable, reason = iterations_comparable(before, after)
    table: dict[str, Any] = {}
    before_dims = _dim_means(before)
    after_dims = _dim_means(after)
    for field in QUALITY_FIELDS:
        left = before_dims.get(field)
        right = after_dims.get(field)
        delta = None
        if left is not None and right is not None:
            delta = round(right - left, 2)
        table[field] = {"before": left, "after": right, "delta": delta}
    robustness = {
        "chatbot_artifacts": (
            _count(before, "chatbot_artifacts"),
            _count(after, "chatbot_artifacts"),
        ),
        "language_mismatch": (
            _count(before, "language_mismatch"),
            _count(after, "language_mismatch"),
        ),
        "truncations": (_count(before, "truncations"), _count(after, "truncations")),
        "runtime_invalid": (
            _count(before, "runtime_invalid"),
            _count(after, "runtime_invalid"),
        ),
        "failed_jobs": (_count(before, "failed_jobs"), _count(after, "failed_jobs")),
        "invalid_jobs": (_count(before, "invalid_jobs"), _count(after, "invalid_jobs")),
    }
    table["robustness"] = {
        name: {"before": pair[0], "after": pair[1], "delta": pair[1] - pair[0]}
        for name, pair in robustness.items()
    }

    if not comparable:
        return {
            "table": table,
            "decision": "INVALID",
            "reason": reason,
            "valid_for_comparison": False,
        }

    after_counts = (after.get("aggregates") or {}).get("counts") or {}
    after_valid = after_counts.get("valid_jobs")
    if after_valid is None:
        aggregates = after.get("aggregates") or {}
        n_jobs = int(aggregates.get("n") or 0)
        failed_jobs = int(aggregates.get("failed") or 0)
        if n_jobs:
            after_valid = max(0, n_jobs - failed_jobs)
        else:
            after_valid = sum(
                1
                for row in after.get("experiments") or []
                if not row.get("error")
                and str(row.get("status") or "")
                in {"", JobStatus.VALID.value}
            )
    for name, pair in robustness.items():
        if pair[1] > pair[0]:
            return {
                "table": table,
                "decision": "REVERT",
                "reason": f"{name} increased {pair[0]} → {pair[1]}",
                "valid_for_comparison": True,
            }

    if after_valid == 0:
        return {
            "table": table,
            "decision": "REVERT",
            "reason": "candidate has zero VALID jobs",
            "valid_for_comparison": True,
        }

    for field in ("fidelity", "coverage", "completeness", "hallucination", "contradiction"):
        delta = table[field]["delta"]
        if delta is None:
            continue
        limit = HALLUCINATION_DROP if field in {"hallucination", "contradiction"} else CRITICAL_DROP
        if delta <= -limit:
            return {
                "table": table,
                "decision": "REVERT",
                "reason": f"{field} dropped {delta}",
                "valid_for_comparison": True,
            }

    docs = (after.get("aggregates") or {}).get("per_document") or {}
    n_docs = len(docs)
    if not n_docs:
        n_docs = len(
            {
                str(row.get("document_id") or row.get("document") or "")
                for row in after.get("experiments") or []
            }
        )
    quality_delta = table["quality_score"]["delta"]
    if quality_delta is None:
        return {
            "table": table,
            "decision": "INCONCLUSIVE",
            "reason": "quality_score unavailable (gold facts missing or no VALID jobs)",
            "valid_for_comparison": True,
        }
    if quality_delta > 0 and n_docs >= MIN_DOCS_FOR_KEEP:
        return {
            "table": table,
            "decision": "KEEP",
            "reason": "quality improved without critical regressions",
            "valid_for_comparison": True,
        }
    if quality_delta > 0:
        return {
            "table": table,
            "decision": "INCONCLUSIVE",
            "reason": (
                f"quality improved but n_documents={n_docs} < {MIN_DOCS_FOR_KEEP}"
            ),
            "valid_for_comparison": True,
        }
    if quality_delta == 0:
        return {
            "table": table,
            "decision": "INCONCLUSIVE",
            "reason": "no material quality change",
            "valid_for_comparison": True,
        }
    return {
        "table": table,
        "decision": "REVERT",
        "reason": f"quality_score dropped {quality_delta}",
        "valid_for_comparison": True,
    }


def iteration_valid_for_comparison(payload: Mapping[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    experiments = payload.get("experiments") or []
    if not experiments:
        return False, ["no experiments"]
    counts = (payload.get("aggregates") or {}).get("counts") or {}
    if int(counts.get("valid_jobs") or 0) == 0:
        reasons.append("zero VALID jobs")
    if int(counts.get("invalid_jobs") or 0) > 0:
        reasons.append("invalid jobs present")
    if int(counts.get("failed_jobs") or 0) > 0:
        reasons.append("failed jobs present")
    if int(counts.get("runtime_invalid") or 0) > 0:
        reasons.append("INVALID_RUNTIME jobs present")
    if int(counts.get("telemetry_missing") or 0) > 0:
        reasons.append("jobs missing telemetry")
    provenance = payload.get("provenance") or {}
    required_meta = (
        "git_sha",
        "dataset_sha",
        "matrix_hash",
        "benchmark_version",
        "scorer_version",
    )
    for key in required_meta:
        if not provenance.get(key):
            reasons.append(f"missing provenance.{key}")
    cells = [tuple(row.get("cell_key") or []) for row in experiments]
    if len(cells) != len(set(cells)):
        reasons.append("duplicate experiment cells")
    if any(not row.get("fingerprint") for row in experiments):
        reasons.append("missing experiment fingerprints")
    telemetry_missing_on_valid = [
        row
        for row in experiments
        if row.get("status") == JobStatus.VALID.value
        and (row.get("telemetry") or {}).get("telemetry_status") != "present"
    ]
    if telemetry_missing_on_valid:
        reasons.append("VALID jobs missing telemetry")
    return (not reasons), reasons
