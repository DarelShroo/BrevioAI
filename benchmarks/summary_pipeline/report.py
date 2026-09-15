from __future__ import annotations

from typing import Any, Mapping


def _fmt(value: Any) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def _mean(block: Mapping[str, Any] | None, field: str) -> Any:
    stats = (block or {}).get(field) or {}
    return stats.get("mean")


def render_report(payload: Mapping[str, Any]) -> str:
    aggregates = payload.get("aggregates") or {}
    counts = aggregates.get("counts") or {}
    quality = aggregates.get("quality") or {}
    cost = aggregates.get("cost") or {}
    comparison = payload.get("comparison") or {}
    validity = payload.get("validity") or {}
    lines = [
        "BENCHMARK RESULT",
        "",
        "VALIDITY",
        "---------",
        f"valid jobs: {counts.get('valid_jobs', 0)}",
        f"invalid jobs: {counts.get('invalid_jobs', 0)}",
        f"failed jobs: {counts.get('failed_jobs', 0)}",
        f"valid_for_comparison: {validity.get('valid_for_comparison', False)}",
        "",
        "QUALITY",
        "-------",
        f"fidelity:       {_fmt(_mean(quality, 'fidelity'))}",
        f"coverage:       {_fmt(_mean(quality, 'coverage'))}",
        f"completeness:   {_fmt(_mean(quality, 'completeness'))}",
        f"hallucination:  {_fmt(_mean(quality, 'hallucination'))}",
        f"contradiction:  {_fmt(_mean(quality, 'contradiction'))}",
        f"utility:        {_fmt(_mean(quality, 'utility'))}",
        f"quality_score:  {_fmt(_mean(quality, 'quality_score'))}",
        "",
        "ROBUSTNESS",
        "----------",
        f"chatbot artifacts: {counts.get('chatbot_artifacts', 0)}",
        f"language mismatch: {counts.get('language_mismatch', 0)}",
        f"truncations: {counts.get('truncations', 0)}",
        f"runtime invalid: {counts.get('runtime_invalid', 0)}",
        "",
        "EFFICIENCY",
        "----------",
        f"median tokens: {_fmt((cost.get('tokens') or {}).get('median'))}",
        f"p90 tokens: {_fmt((cost.get('tokens') or {}).get('p90'))}",
        f"median latency: {_fmt((cost.get('seconds') or {}).get('median'))}",
        f"retry mean: {_fmt((cost.get('retries') or {}).get('mean'))}",
        "",
        "COST",
        "----",
        f"provider cost: {_fmt((cost.get('provider_cost') or {}).get('mean'))}",
        f"jobs with telemetry: {cost.get('jobs_with_telemetry', 0)}",
        f"jobs missing telemetry: {cost.get('jobs_missing_telemetry', 0)}",
        "",
        "COMPARISON",
        "----------",
        f"baseline: {comparison.get('baseline_id') or 'none'}",
        f"candidate: {payload.get('iteration_id')}",
        "",
        "DECISION",
        "--------",
        f"{comparison.get('decision') or 'INCONCLUSIVE'}",
        f"{comparison.get('reason') or ''}",
    ]
    return "\n".join(lines).rstrip() + "\n"
