"""Normalize provider response/error usage into a common structure."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class NormalizedUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0
    audio_tokens: int = 0
    provider_request_id: Optional[str] = None
    finish_reason: Optional[str] = None
    usage_source: str = "UNAVAILABLE"


def _as_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _dig(obj: Any, *names: str) -> Any:
    for name in names:
        if obj is None:
            return None
        if isinstance(obj, dict):
            if name in obj:
                return obj[name]
        else:
            if hasattr(obj, name):
                return getattr(obj, name)
    return None


def normalize_provider_usage(response: Any = None, *, exc: BaseException | None = None) -> NormalizedUsage:
    """Extract usage from OpenAI-compatible / Anthropic / Gemini / Ollama shapes.

    Never invents tokens. Missing usage → usage_source=UNAVAILABLE.
    """
    if response is None and exc is not None:
        # Some SDKs attach a partial response on the exception.
        response = getattr(exc, "response", None) or getattr(exc, "body", None)

    if response is None:
        return NormalizedUsage()

    usage = _dig(response, "usage")
    # Gemini generative style
    if usage is None:
        usage = _dig(response, "usage_metadata", "usageMetadata")

    request_id = _dig(response, "id", "request_id", "response_id")
    if request_id is not None:
        request_id = str(request_id)

    finish_reason = None
    choices = _dig(response, "choices")
    if choices and len(choices) > 0:
        finish_reason = _dig(choices[0], "finish_reason", "finishReason")
        if finish_reason is not None:
            finish_reason = str(finish_reason)

    if usage is None:
        # Ollama native fields sometimes live on the root.
        prompt_eval = _as_int(_dig(response, "prompt_eval_count"))
        eval_count = _as_int(_dig(response, "eval_count"))
        if prompt_eval is None and eval_count is None:
            return NormalizedUsage(
                provider_request_id=request_id,
                finish_reason=finish_reason,
                usage_source="UNAVAILABLE",
            )
        inp = prompt_eval or 0
        out = eval_count or 0
        return NormalizedUsage(
            input_tokens=inp,
            output_tokens=out,
            total_tokens=inp + out,
            provider_request_id=request_id,
            finish_reason=finish_reason,
            usage_source="REAL",
        )

    input_tokens = (
        _as_int(_dig(usage, "prompt_tokens", "input_tokens", "promptTokenCount"))
        or 0
    )
    output_tokens = (
        _as_int(
            _dig(
                usage,
                "completion_tokens",
                "output_tokens",
                "candidatesTokenCount",
                "candidates_token_count",
            )
        )
        or 0
    )
    total_tokens = _as_int(_dig(usage, "total_tokens", "totalTokenCount"))
    if total_tokens is None:
        total_tokens = input_tokens + output_tokens

    cached = 0
    details = _dig(usage, "prompt_tokens_details", "input_tokens_details")
    if details is not None:
        cached = _as_int(_dig(details, "cached_tokens", "cache_read_input_tokens")) or 0
    if cached == 0:
        cached = (
            _as_int(
                _dig(
                    usage,
                    "cached_tokens",
                    "cache_read_input_tokens",
                    "cachedContentTokenCount",
                )
            )
            or 0
        )

    reasoning = 0
    out_details = _dig(usage, "completion_tokens_details", "output_tokens_details")
    if out_details is not None:
        reasoning = _as_int(_dig(out_details, "reasoning_tokens")) or 0
    if reasoning == 0:
        reasoning = _as_int(_dig(usage, "reasoning_tokens", "thoughtsTokenCount")) or 0

    audio = 0
    if details is not None:
        audio = _as_int(_dig(details, "audio_tokens")) or 0

    has_any = (
        input_tokens > 0
        or output_tokens > 0
        or total_tokens > 0
        or cached > 0
        or reasoning > 0
    )
    return NormalizedUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cached_input_tokens=cached,
        reasoning_tokens=reasoning,
        audio_tokens=audio,
        provider_request_id=request_id,
        finish_reason=finish_reason,
        usage_source="REAL" if has_any else "UNAVAILABLE",
    )
