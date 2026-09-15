from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import httpx

from core.brevio.services.summary_providers.provider import CompletionRequest
from core.shared.enums.model import ModelType
from core.shared.utils.model_capabilities import get_model_capabilities

ANTHROPIC_VERSION = "2023-06-01"


@dataclass
class _Usage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class _Message:
    content: str


@dataclass
class _Choice:
    message: _Message
    finish_reason: Optional[str]


@dataclass
class AnthropicChatCompletion:
    """Shape consumed by SummaryService (OpenAI ChatCompletion fields)."""

    choices: list[_Choice]
    usage: _Usage


def _finish_reason(stop_reason: Optional[str]) -> Optional[str]:
    if stop_reason == "end_turn":
        return "stop"
    if stop_reason == "max_tokens":
        return "length"
    return stop_reason


def _text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    parts: list[str] = []
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
            elif hasattr(block, "text"):
                parts.append(str(getattr(block, "text") or ""))
    return "".join(parts)


def _split_messages(
    messages: list[dict[str, Any]]
) -> tuple[Optional[str], list[dict[str, Any]]]:
    system_parts: list[str] = []
    converted: list[dict[str, Any]] = []
    for item in messages:
        role = str(item.get("role") or "user")
        text = item.get("content") or ""
        if role == "system":
            system_parts.append(str(text))
            continue
        if role not in {"user", "assistant"}:
            role = "user"
        converted.append({"role": role, "content": str(text)})
    system = "\n\n".join(part for part in system_parts if part) or None
    return system, converted


class AnthropicSummaryProvider:
    provider_id = "anthropic"
    requires_api_key = True
    is_local = False

    async def complete(self, client: Any, request: CompletionRequest) -> Any:
        api_key = getattr(client, "api_key", None)
        if not api_key:
            raise ValueError("Anthropic API key is missing")
        base_url = str(getattr(client, "base_url", "") or "https://api.anthropic.com")
        root = base_url.rstrip("/")
        if root.endswith("/v1"):
            root = root[:-3]
        url = f"{root}/v1/messages"
        system, messages = _split_messages(request.messages)
        payload: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "messages": messages,
        }
        if system:
            payload["system"] = system
        model = ModelType(request.model)
        caps = get_model_capabilities(model)
        extra = dict(request.extra or {})
        effort = extra.pop("effort", None) or extra.pop("reasoning_effort", None)
        if caps.reasoning == "effort" and effort:
            payload["output_config"] = {"effort": effort}
        if caps.supports_temperature:
            payload["temperature"] = request.temperature
        timeout = request.timeout or 120.0
        async with httpx.AsyncClient(timeout=timeout) as http:
            response = await http.post(
                url,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": ANTHROPIC_VERSION,
                    "content-type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        text = _text_from_content(body.get("content"))
        usage_raw = body.get("usage") or {}
        prompt_tokens = int(usage_raw.get("input_tokens") or 0)
        completion_tokens = int(usage_raw.get("output_tokens") or 0)
        return AnthropicChatCompletion(
            choices=[
                _Choice(
                    message=_Message(content=text),
                    finish_reason=_finish_reason(body.get("stop_reason")),
                )
            ],
            usage=_Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
        )
