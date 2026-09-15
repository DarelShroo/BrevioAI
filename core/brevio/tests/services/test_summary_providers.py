from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from core.brevio.services.summary_providers.openai_compatible import (
    OllamaSummaryProvider,
    OpenAISummaryProvider,
)
from core.brevio.services.summary_providers.provider import CompletionRequest


@pytest.mark.asyncio
async def test_openai_compatible_complete_delegates_to_client() -> None:
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value="completion")
    provider = OpenAISummaryProvider()
    result = await provider.complete(
        client,
        CompletionRequest(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=16,
            temperature=0.2,
            extra={"foo": 1},
            timeout=5,
        ),
    )
    assert result == "completion"
    client.chat.completions.create.assert_awaited()
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["foo"] == 1


def test_ollama_provider_is_local() -> None:
    provider = OllamaSummaryProvider()
    assert provider.is_local is True
    assert provider.requires_api_key is False
    assert provider.provider_id == "ollama"
