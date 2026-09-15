from __future__ import annotations

from typing import Any, Mapping


def baseline_from_iteration(payload: Mapping[str, Any]) -> dict[str, Any]:
    provenance = payload.get("provenance") or {}
    validity = payload.get("validity") or {}
    return {
        "baseline_id": payload.get("iteration_id"),
        "dataset_sha": provenance.get("dataset_sha"),
        "matrix_sha": provenance.get("matrix_hash"),
        "git_sha": provenance.get("git_sha"),
        "model_digest": provenance.get("model_digest"),
        "prompt_hash": provenance.get("prompt_hash"),
        "runtime": {
            "requested_context": provenance.get("requested_context"),
            "effective_context": provenance.get("effective_context"),
        },
        "scores": (payload.get("aggregates") or {}).get("quality"),
        "valid_for_comparison": bool(validity.get("valid_for_comparison")),
        "scorer_version": provenance.get("scorer_version"),
        "judge_version": provenance.get("judge_version"),
        "benchmark_version": provenance.get("benchmark_version"),
    }
