from __future__ import annotations

from typing import Dict

from core.brevio.services.summary_providers.anthropic import AnthropicSummaryProvider
from core.brevio.services.summary_providers.openai_compatible import (
    DeepSeekSummaryProvider,
    GeminiSummaryProvider,
    OllamaSummaryProvider,
    OpenAISummaryProvider,
    XAISummaryProvider,
    RunAISummaryProvider,
)
from core.brevio.services.summary_providers.provider import SummaryProvider


class SummaryProviderRegistry:
    def __init__(self) -> None:
        self._providers: Dict[str, SummaryProvider] = {
            "openai": OpenAISummaryProvider(),
            "deepseek": DeepSeekSummaryProvider(),
            "google": GeminiSummaryProvider(),
            "xai": XAISummaryProvider(),
            "anthropic": AnthropicSummaryProvider(),
            "ollama": OllamaSummaryProvider(),
            "runai": RunAISummaryProvider(),
        }

    def get(self, provider: str) -> SummaryProvider:
        adapter = self._providers.get(provider.strip().lower())
        if adapter is None:
            raise ValueError(f"Summary provider {provider} is not supported")
        return adapter
