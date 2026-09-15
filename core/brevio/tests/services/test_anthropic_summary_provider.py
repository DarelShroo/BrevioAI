from unittest.mock import MagicMock, patch

import pytest

from core.brevio.services.summary_providers.anthropic import AnthropicSummaryProvider
from core.brevio.services.summary_providers.provider import CompletionRequest
from core.shared.enums.model import ModelType


@pytest.mark.asyncio
async def test_anthropic_adapter_maps_messages_and_effort() -> None:
    captured: dict = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "content": [{"type": "text", "text": "ok"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 4},
            }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    client = MagicMock(api_key="sk-ant-test", base_url="https://api.anthropic.com")
    provider = AnthropicSummaryProvider()
    with patch(
        "core.brevio.services.summary_providers.anthropic.httpx.AsyncClient",
        return_value=FakeClient(),
    ):
        result = await provider.complete(
            client,
            CompletionRequest(
                model=ModelType.CLAUDE_SONNET_5.value,
                messages=[
                    {"role": "system", "content": "sys"},
                    {"role": "user", "content": "hi"},
                ],
                max_tokens=128,
                temperature=0.9,
                extra={"effort": "high"},
            ),
        )
    assert result.choices[0].message.content == "ok"
    assert result.choices[0].finish_reason == "stop"
    assert "temperature" not in captured["json"]
    assert captured["json"]["system"] == "sys"
    assert captured["json"]["max_tokens"] == 128
    assert captured["json"]["output_config"] == {"effort": "high"}
    assert captured["headers"]["x-api-key"] == "sk-ant-test"
    assert captured["headers"]["anthropic-version"] == "2023-06-01"


@pytest.mark.asyncio
async def test_anthropic_haiku_sends_temperature_not_effort() -> None:
    captured: dict = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "content": [{"type": "text", "text": "haiku"}],
                "stop_reason": "max_tokens",
                "usage": {"input_tokens": 2, "output_tokens": 1},
            }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, headers=None, json=None):
            captured["json"] = json
            return FakeResponse()

    client = MagicMock(api_key="sk-ant-test", base_url="https://api.anthropic.com")
    provider = AnthropicSummaryProvider()
    with patch(
        "core.brevio.services.summary_providers.anthropic.httpx.AsyncClient",
        return_value=FakeClient(),
    ):
        result = await provider.complete(
            client,
            CompletionRequest(
                model=ModelType.CLAUDE_HAIKU_4_5.value,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=64,
                temperature=0.3,
                extra={"effort": "high"},
            ),
        )
    assert result.choices[0].finish_reason == "length"
    assert captured["json"]["temperature"] == 0.3
    assert "output_config" not in captured["json"]
