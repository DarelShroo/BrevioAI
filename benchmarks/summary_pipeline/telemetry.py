from __future__ import annotations

from typing import Any, Mapping

from .models import TelemetrySnapshot


def load_logs(logs_json) -> list[dict[str, Any]]:
    from pathlib import Path

    path = Path(logs_json)
    if not path.is_file():
        return []
    import json

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def telemetry_appears_missing(raw: Mapping[str, Any] | None) -> bool:
    if not raw:
        return True
    status = str(raw.get("telemetry_status") or "")
    if status == "missing":
        return True
    if status == "present":
        return False
    model = str(raw.get("model") or "").strip()
    numeric = [
        raw.get("total_tokens_summary_input"),
        raw.get("total_tokens_summary_output"),
        raw.get("api_request_count"),
        raw.get("number_of_chunks"),
        raw.get("num_tokens_file"),
    ]
    zeros = all(item in (0, 0.0, None, "") for item in numeric)
    return (not model) and zeros


def snapshot_from_mapping(raw: Mapping[str, Any] | None) -> TelemetrySnapshot:
    payload = dict(raw or {})
    folder_id = str(payload.get("folder_id") or payload.get("folder_entry_id") or "")
    if telemetry_appears_missing(payload):
        return TelemetrySnapshot(folder_id=folder_id, telemetry_status="missing")
    known = set(TelemetrySnapshot.__dataclass_fields__)
    fields = {key: value for key, value in payload.items() if key in known}
    fields["folder_id"] = folder_id
    fields["telemetry_status"] = "present"
    cost = fields.get("estimated_provider_cost")
    if not fields.get("pricing_version") and cost in (None, 0, 0.0, ""):
        fields["estimated_provider_cost"] = None
    try:
        return TelemetrySnapshot(**fields)
    except TypeError:
        return TelemetrySnapshot(folder_id=folder_id, telemetry_status="present")


def snapshot_for_folder(logs_json, folder_id: str) -> TelemetrySnapshot:
    if not folder_id:
        return TelemetrySnapshot(folder_id="", telemetry_status="missing")
    entries = [
        item
        for item in load_logs(logs_json)
        if str(item.get("folder_id") or "") == folder_id
    ]
    if not entries:
        return TelemetrySnapshot(folder_id=folder_id, telemetry_status="missing")
    entry = entries[-1]
    history = list(entry.get("history_tokens_per_call") or [])
    calls_by_type: dict[str, int] = {}
    wasted = 0
    for call in history:
        kind = str(call.get("type_call") or "unknown")
        calls_by_type[kind] = calls_by_type.get(kind, 0) + 1
        finish = str(call.get("finish_reason") or "")
        if finish in {"length", "max_tokens"}:
            wasted += int(call.get("response_tokens") or 0)
    retries = _optional_int(entry.get("retry_requests"))
    retry_tokens: int | None
    if retries is None:
        retry_tokens = None
    elif retries == 0:
        retry_tokens = 0
    else:
        retry_tokens = None
    pricing_version = str(entry.get("pricing_version") or "") or None
    raw_cost = _optional_float(entry.get("estimated_provider_cost"))
    if pricing_version is None and (raw_cost is None or raw_cost == 0.0):
        cost: float | None = None
    else:
        cost = raw_cost
    return TelemetrySnapshot(
        folder_id=str(entry.get("folder_id") or folder_id),
        telemetry_status="present",
        model=str(entry.get("model") or "") or None,
        language_input=str(entry.get("language_input") or "") or None,
        language_output=str(entry.get("language_output") or "") or None,
        category=str(entry.get("category") or "") or None,
        style=str(entry.get("style") or "") or None,
        summary_level=str(entry.get("summary_level") or "") or None,
        num_tokens_file=_optional_int(entry.get("num_tokens_file")),
        num_chars_file=_optional_int(entry.get("num_chars_file")),
        number_of_chunks=_optional_int(entry.get("number_of_chunks")),
        route=str(entry.get("route") or "") or None,
        map_requests=_optional_int(entry.get("map_requests")),
        reduce_requests=_optional_int(entry.get("reduce_requests")),
        format_requests=_optional_int(entry.get("format_requests")),
        direct_requests=_optional_int(entry.get("direct_requests")),
        api_request_count=_optional_int(entry.get("api_request_count")),
        retry_requests=retries,
        failed_requests=_optional_int(entry.get("failed_requests")),
        connectivity_probes=_optional_int(entry.get("connectivity_probes")),
        truncation_detected=bool(entry.get("truncation_detected")),
        total_tokens_summary_input=_optional_int(
            entry.get("total_tokens_summary_input")
        ),
        total_tokens_summary_output=_optional_int(
            entry.get("total_tokens_summary_output")
        ),
        total_tokens_postprocess_input=_optional_int(
            entry.get("total_tokens_postprocess_input")
        ),
        total_tokens_postprocess_output=_optional_int(
            entry.get("total_tokens_postprocess_output")
        ),
        total_time=_optional_float(entry.get("total_time")),
        output_min_tokens=_optional_int(entry.get("output_min_tokens")),
        output_target_tokens=_optional_int(entry.get("output_target_tokens")),
        output_max_tokens=_optional_int(entry.get("output_max_tokens")),
        pipeline_status=str(entry.get("pipeline_status") or "") or None,
        pipeline_phase=str(entry.get("pipeline_phase") or "") or None,
        phase_token_totals=dict(entry.get("phase_token_totals") or {}),
        calls_by_type=calls_by_type,
        wasted_retry_tokens=wasted,
        retry_tokens=retry_tokens,
        physical_http_requests=_optional_int(entry.get("physical_http_requests")),
        estimated_provider_cost=cost,
        cost_currency=str(entry.get("cost_currency") or "") or None,
        pricing_version=pricing_version,
        phase_prompt_hashes=dict(entry.get("phase_prompt_hashes") or {}),
        token_accounting="hybrid_encoder_input_plus_api_output",
        history_tokens_per_call=history,
    )
