from __future__ import annotations

from typing import Any, Optional

from core.shared.enums.model import ModelType
from core.shared.utils.model_capabilities import (
    generation_parameter_ids,
    get_model_capabilities,
)


class GenerationParamError(ValueError):
    """User-supplied generation parameter is incompatible with the selected model."""


def validate_generation_params(
    model: ModelType,
    *,
    max_output_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    reasoning_effort: Optional[str] = None,
    effort: Optional[str] = None,
) -> None:
    # Sampling and output caps are official per-model backend values.
    _ = max_output_tokens
    _ = temperature
    caps = get_model_capabilities(model)
    allowed = set(generation_parameter_ids(caps))

    reasoning_value = reasoning_effort if reasoning_effort is not None else effort
    reasoning_key = caps.reasoning
    if reasoning_value is not None:
        if not reasoning_key or reasoning_key not in allowed:
            raise GenerationParamError(
                f"Model '{model.value}' does not accept a reasoning parameter"
            )
        if reasoning_value not in caps.reasoning_values:
            raise GenerationParamError(
                f"Unsupported {reasoning_key} '{reasoning_value}' for model '{model.value}'"
            )


def chat_completion_kwargs(
    model: ModelType,
    *,
    messages: list[dict[str, Any]],
    max_tokens: int,
    temperature: float,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Translate internal completion fields to Chat Completions kwargs for this model."""
    caps = get_model_capabilities(model)
    kwargs: dict[str, Any] = {
        "model": model.value,
        "messages": messages,
        caps.output_token_param: max_tokens,
    }
    if caps.supports_temperature:
        kwargs["temperature"] = temperature
    merged = dict(extra or {})
    if caps.output_token_param != "max_tokens":
        merged.pop("max_tokens", None)
    if not caps.supports_temperature:
        merged.pop("temperature", None)
    if caps.reasoning != "reasoning_effort":
        merged.pop("reasoning_effort", None)
    if caps.reasoning != "effort":
        merged.pop("effort", None)
    kwargs.update(merged)
    return kwargs
