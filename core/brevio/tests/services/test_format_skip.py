"""FORMAT skip: opt-in via BREVIO_ENABLE_FORMAT_PHASE, then min_tokens threshold."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.brevio.enums.language import LanguageType
from core.brevio.services.summary_service import SummaryService
from core.shared.enums.model import ModelType


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    monkeypatch.setattr(
        "core.brevio_api.core.database.AsyncDB.database", lambda self: MagicMock()
    )


@pytest.fixture
def service():
    return SummaryService()


def test_should_skip_formatting_when_disabled_by_default(service, monkeypatch):
    monkeypatch.delenv("BREVIO_ENABLE_FORMAT_PHASE", raising=False)
    monkeypatch.setenv("BREVIO_MIN_TOKENS_FOR_POSTPROCESS", "0")
    text = "one two three four five six " * 40
    assert service._should_skip_formatting(text, ModelType.GPT_4O_MINI) is True


def test_should_skip_formatting_below_threshold_when_enabled(service, monkeypatch):
    monkeypatch.setenv("BREVIO_ENABLE_FORMAT_PHASE", "1")
    monkeypatch.setenv("BREVIO_MIN_TOKENS_FOR_POSTPROCESS", "50")
    short = "short reduced summary"
    assert service._should_skip_formatting(short, ModelType.GPT_4O_MINI) is True


def test_should_run_formatting_when_enabled_and_above_threshold(service, monkeypatch):
    monkeypatch.setenv("BREVIO_ENABLE_FORMAT_PHASE", "1")
    monkeypatch.setenv("BREVIO_MIN_TOKENS_FOR_POSTPROCESS", "3")
    text = "one two three four five six"
    assert service._should_skip_formatting(text, ModelType.GPT_4O_MINI) is False


@pytest.mark.asyncio
async def test_run_formatting_phase_still_calls_llm_when_invoked_directly(service):
    """Skip is orchestration-level; run_formatting_phase itself still formats."""
    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(
            message=MagicMock(content="# Formatted\n\nBody."), finish_reason="stop"
        )
    ]
    mock_resp.usage = MagicMock(total_tokens=20, completion_tokens=8)
    service.client = MagicMock()
    service.client.chat.completions.create = AsyncMock(return_value=mock_resp)
    with patch.object(service, "_check_token_limit", return_value=True), patch.object(
        service.api_service, "_initialize_client", return_value=service.client
    ):
        result, tokens = await service.run_formatting_phase(
            "Raw factual text",
            "Format prompt",
            ModelType.DEEPSEEK_V4_PRO,
            LanguageType.ENGLISH,
        )
    assert result == "# Formatted\n\nBody."
    assert tokens == 20
    service.client.chat.completions.create.assert_awaited()
