from __future__ import annotations

import asyncio
from typing import Any

from core.brevio.services.summary_providers.provider import CompletionRequest
from core.shared.enums.model import ModelType
from core.shared.utils.generation_params import chat_completion_kwargs


class OpenAICompatibleSummaryProvider:
    """Chat Completions via an OpenAI-compatible client.

    OpenAI, DeepSeek, Gemini, xAI, and Ollama share this transport.
    Anthropic uses a native Messages adapter instead.
    """

    provider_id: str = "openai"
    requires_api_key: bool = True
    is_local: bool = False

    async def complete(self, client: Any, request: CompletionRequest) -> Any:
        model = ModelType(request.model)
        kwargs = chat_completion_kwargs(
            model,
            messages=request.messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            extra=request.extra,
        )
        return await asyncio.wait_for(
            client.chat.completions.create(**kwargs),
            timeout=request.timeout,
        )


class OpenAISummaryProvider(OpenAICompatibleSummaryProvider):
    provider_id = "openai"


class DeepSeekSummaryProvider(OpenAICompatibleSummaryProvider):
    provider_id = "deepseek"


class GeminiSummaryProvider(OpenAICompatibleSummaryProvider):
    provider_id = "google"


class XAISummaryProvider(OpenAICompatibleSummaryProvider):
    provider_id = "xai"


class OllamaSummaryProvider(OpenAICompatibleSummaryProvider):
    provider_id = "ollama"
    requires_api_key = False
    is_local = True


class RunAISummaryProvider(OpenAICompatibleSummaryProvider):
    provider_id = "runai"
    requires_api_key = False
    is_local = True
