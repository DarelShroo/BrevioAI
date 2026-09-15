from unittest.mock import AsyncMock, MagicMock

import pytest

from core.brevio.services.summary_providers.openai_compatible import (
    OpenAISummaryProvider,
)
from core.brevio.services.summary_providers.provider import CompletionRequest
from core.shared.enums.model import ModelType


@pytest.mark.asyncio
async def test_openai_compatible_provider_uses_model_specific_kwargs() -> None:
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value="ok")
    provider = OpenAISummaryProvider()
    result = await provider.complete(
        client,
        CompletionRequest(
            model=ModelType.GPT_5_6.value,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=32,
            temperature=0.9,
            extra={"reasoning_effort": "low"},
        ),
    )
    assert result == "ok"
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["max_completion_tokens"] == 32
    assert "max_tokens" not in kwargs
    assert "temperature" not in kwargs
    assert kwargs["reasoning_effort"] == "low"
