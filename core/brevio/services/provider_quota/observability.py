"""Structured 429 / rate-limit signal extraction. Never logs API keys."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Mapping, Optional

logger = logging.getLogger(__name__)


@dataclass
class RateLimitSignals:
    status_code: Optional[int] = None
    headers: dict[str, str] = field(default_factory=dict)
    retry_after_seconds: Optional[float] = None
    retry_after_ms: Optional[float] = None
    wait_seconds: Optional[float] = None
    body: Any = None
    quota_metric: Optional[str] = None
    quota_id: Optional[str] = None
    reason: Optional[str] = None
    error_code: Optional[str] = None


def _headers_to_dict(headers: Any) -> dict[str, str]:
    if headers is None:
        return {}
    try:
        return {str(k).lower(): str(v) for k, v in headers.items()}
    except Exception:
        return {}


def _parse_http_date_delay(value: str) -> Optional[float]:
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delay = (dt - datetime.now(timezone.utc)).total_seconds()
        return max(delay, 0.0)
    except Exception:
        return None


def parse_retry_after_headers(
    headers: Mapping[str, str]
) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Return (retry_after_ms_header, retry_after_seconds_header, resolved_wait_seconds)."""
    normalized = {str(k).lower(): str(v) for k, v in headers.items()}
    retry_after_ms: Optional[float] = None
    retry_after_seconds: Optional[float] = None
    wait_seconds: Optional[float] = None

    raw_ms = normalized.get("retry-after-ms")
    if raw_ms is not None:
        try:
            retry_after_ms = float(raw_ms)
            wait_seconds = retry_after_ms / 1000.0
        except ValueError:
            pass

    raw = normalized.get("retry-after")
    if raw is not None:
        try:
            retry_after_seconds = float(raw)
            if wait_seconds is None:
                wait_seconds = retry_after_seconds
        except ValueError:
            date_delay = _parse_http_date_delay(raw)
            if date_delay is not None:
                retry_after_seconds = date_delay
                if wait_seconds is None:
                    wait_seconds = date_delay

    return retry_after_ms, retry_after_seconds, wait_seconds


_DURATION_RE = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*(ms|s|m|sec|secs|second|seconds|minute|minutes)?\s*$",
    re.IGNORECASE,
)
_RETRY_IN_RE = re.compile(
    r"retry(?:\s+after)?\s+in\s+(\d+(?:\.\d+)?)\s*(ms|s|m|sec|secs|seconds|minutes)?",
    re.IGNORECASE,
)
_RETRY_DELAY_KEYS = {
    "retrydelay",
    "retrydelayseconds",
    "retryafter",
    "retryafterseconds",
}
_MAX_PARSED_WAIT_SECONDS = 300.0


def parse_duration_seconds(value: Any) -> Optional[float]:
    """Parse provider duration values: 32, '32s', '1.5s', '500ms', {seconds, nanos}."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if value < 0:
            return None
        return float(value)
    if isinstance(value, dict):
        try:
            seconds = float(value.get("seconds") or 0)
            nanos = float(value.get("nanos") or 0)
            return max(0.0, seconds + nanos / 1e9)
        except (TypeError, ValueError):
            return None
    if not isinstance(value, str):
        return None
    match = _DURATION_RE.match(value.strip())
    if not match:
        return None
    amount = float(match.group(1))
    unit = (match.group(2) or "s").lower()
    if unit == "ms":
        return amount / 1000.0
    if unit in ("m", "minute", "minutes"):
        return amount * 60.0
    return amount


def _unwrap_error_payload(body: Any) -> Any:
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except Exception:
            return body
    if isinstance(body, list) and body:
        return _unwrap_error_payload(body[0])
    return body


def parse_retry_delay_from_body(body: Any) -> Optional[float]:
    """Wait extraction from any 429 JSON: RetryInfo.retryDelay, retry_after, message."""
    waits: list[float] = []

    def _consider(raw: Any) -> None:
        parsed = parse_duration_seconds(raw)
        if parsed is not None and 0 < parsed <= _MAX_PARSED_WAIT_SECONDS:
            waits.append(parsed)

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                compact = str(key).lower().replace("-", "").replace("_", "")
                if compact in _RETRY_DELAY_KEYS:
                    _consider(value)
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)
        elif isinstance(node, str):
            for match in _RETRY_IN_RE.finditer(node):
                amount = match.group(1)
                unit = match.group(2) or "s"
                _consider(f"{amount}{unit}")

    _walk(_unwrap_error_payload(body))
    return max(waits) if waits else None


def _extract_quota_fields(
    body: Any,
) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    metric = quota_id = reason = error_code = None
    if body is None:
        return metric, quota_id, reason, error_code

    data = _unwrap_error_payload(body)
    if isinstance(data, str):
        reason = data[:500] if data else None
        return metric, quota_id, reason, error_code

    if not isinstance(data, dict):
        return metric, quota_id, reason, error_code

    err = data.get("error") if isinstance(data.get("error"), dict) else data
    if isinstance(err, dict):
        error_code = err.get("code") or err.get("status") or data.get("code")
        reason = err.get("message") or err.get("status") or data.get("message")
        details = err.get("details") or data.get("details") or []
        if isinstance(details, list):
            for item in details:
                if not isinstance(item, dict):
                    continue
                metric = metric or item.get("quotaMetric") or item.get("quota_metric")
                quota_id = quota_id or item.get("quotaId") or item.get("quota_id")
                violations = item.get("violations")
                if isinstance(violations, list):
                    for violation in violations:
                        if not isinstance(violation, dict):
                            continue
                        metric = (
                            metric
                            or violation.get("quotaMetric")
                            or violation.get("quota_metric")
                        )
                        quota_id = (
                            quota_id
                            or violation.get("quotaId")
                            or violation.get("quota_id")
                        )
        meta = err.get("metadata") if isinstance(err.get("metadata"), dict) else {}
        metric = metric or meta.get("quota_metric") or meta.get("quotaMetric")
        quota_id = quota_id or meta.get("quota_id") or meta.get("quotaId")

    return (
        str(metric) if metric else None,
        str(quota_id) if quota_id else None,
        str(reason) if reason else None,
        str(error_code) if error_code else None,
    )


def extract_rate_limit_signals(exc: BaseException) -> RateLimitSignals:
    """Best-effort extraction from openai.RateLimitError / httpx / generic exceptions."""
    status_code: Optional[int] = getattr(exc, "status_code", None)
    response = getattr(exc, "response", None)
    headers: dict[str, str] = {}
    body: Any = getattr(exc, "body", None)

    if response is not None:
        headers = _headers_to_dict(getattr(response, "headers", None))
        if status_code is None:
            status_code = getattr(response, "status_code", None)
        if body is None:
            try:
                text = getattr(response, "text", None)
                if callable(text):
                    # unlikely
                    body = None
                elif text:
                    body = text
                else:
                    body = None
            except Exception:
                body = None
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except Exception:
                    pass

    if status_code is None and "429" in str(exc):
        status_code = 429

    retry_after_ms, retry_after_seconds, wait_seconds = parse_retry_after_headers(
        headers
    )
    body_wait = parse_retry_delay_from_body(body)
    if body_wait is not None:
        wait_seconds = (
            body_wait if wait_seconds is None else max(wait_seconds, body_wait)
        )
    quota_metric, quota_id, reason, error_code = _extract_quota_fields(body)

    return RateLimitSignals(
        status_code=status_code,
        headers=headers,
        retry_after_seconds=retry_after_seconds,
        retry_after_ms=retry_after_ms,
        wait_seconds=wait_seconds,
        body=body,
        quota_metric=quota_metric,
        quota_id=quota_id,
        reason=reason,
        error_code=error_code,
    )


def get_celery_task_id() -> Optional[str]:
    try:
        from celery import current_task

        if current_task is None or current_task.request is None:
            return None
        return getattr(current_task.request, "id", None)
    except Exception:
        return None


def sanitize_scope_for_log(quota_scope_id: str) -> str:
    """Ensure we never log raw API keys if misconfigured."""
    if not quota_scope_id:
        return "unknown"
    lowered = quota_scope_id.lower()
    if lowered.startswith("sk-") or "api" in lowered and len(quota_scope_id) > 40:
        return "redacted"
    return quota_scope_id


def log_provider_429(
    *,
    signals: RateLimitSignals,
    provider: str,
    model: str,
    quota_scope_id: str,
    phase: str,
    chunk_id: Optional[str] = None,
    retry_number: int = 0,
    worker_pid: Optional[int] = None,
    celery_task_id: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> None:
    payload = {
        "event": "provider_429",
        "status_code": signals.status_code,
        "provider": provider,
        "model": model,
        "quota_scope_id": sanitize_scope_for_log(quota_scope_id),
        "phase": phase,
        "chunk_id": chunk_id,
        "celery_task_id": celery_task_id
        if celery_task_id is not None
        else get_celery_task_id(),
        "worker_pid": worker_pid if worker_pid is not None else os.getpid(),
        "retry_number": retry_number,
        "retry_after": signals.retry_after_seconds,
        "retry_after_ms": signals.retry_after_ms,
        "wait_seconds": signals.wait_seconds,
        "quota_metric": signals.quota_metric,
        "quota_id": signals.quota_id,
        "reason": signals.reason,
        "error_code": signals.error_code,
        "headers": {
            k: v
            for k, v in signals.headers.items()
            if "key" not in k and "auth" not in k and "token" not in k
        },
        "body": signals.body,
    }
    if extra:
        payload.update(extra)
    # Never include api_key-like fields
    for forbidden in ("api_key", "apiKey", "authorization", "Authorization"):
        payload.pop(forbidden, None)
    logger.warning("event=provider_429 %s", json.dumps(payload, default=str)[:8000])


def signals_as_dict(signals: RateLimitSignals) -> dict[str, Any]:
    return asdict(signals)
