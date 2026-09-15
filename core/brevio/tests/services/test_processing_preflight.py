from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from core.brevio.services.processing_preflight import ProcessingPreflight
from core.brevio.services.summary_providers.registry import SummaryProviderRegistry
from core.brevio.services.transcription.errors import TranscriptionError
from core.brevio_api.models.errors.api_codes import ApiErrorCode
from core.brevio_api.models.errors.provider_errors import (
    ProviderError,
    ProviderErrorKind,
)
from core.shared.enums.model import ModelType


@pytest.mark.asyncio
async def test_preflight_documents_skips_transcription() -> None:
    resolver = MagicMock()
    resolver.ensure_model_access = AsyncMock()
    resolver.ensure_user_credential = AsyncMock()
    decision = await ProcessingPreflight(resolver).ensure(
        source_type="documents",
        user_id="u1",
        model=ModelType.GPT_4O_MINI,
        user_credits=5,
    )
    assert decision.needs_transcription is False
    assert decision.transcription_provider is None
    resolver.ensure_model_access.assert_awaited()
    resolver.ensure_user_credential.assert_not_called()


@pytest.mark.asyncio
async def test_preflight_media_requires_openai_byok(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("WHISPER_LOCAL_USER_ACCESS", raising=False)
    resolver = MagicMock()
    resolver.ensure_model_access = AsyncMock()
    resolver.ensure_user_credential = AsyncMock(
        side_effect=ProviderError(
            kind=ProviderErrorKind.USER_CREDENTIAL_REQUIRED, message="missing"
        )
    )
    with pytest.raises(TranscriptionError) as exc:
        await ProcessingPreflight(resolver).ensure(
            source_type="youtube",
            user_id="u1",
            model=ModelType.GPT_4O_MINI,
            user_credits=5,
        )
    assert exc.value.code == ApiErrorCode.TRANSCRIPTION_API_KEY_REQUIRED.value
    resolver.ensure_user_credential.assert_awaited_once()


@pytest.mark.asyncio
async def test_preflight_youtube_resolves_default_openai_in_prod(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("WHISPER_LOCAL_USER_ACCESS", raising=False)
    resolver = MagicMock()
    resolver.ensure_model_access = AsyncMock()
    resolver.ensure_user_credential = AsyncMock()
    decision = await ProcessingPreflight(resolver).ensure(
        source_type="youtube",
        user_id="u1",
        model=ModelType.GPT_4O_MINI,
        user_credits=5,
    )
    assert decision.needs_transcription is True
    assert decision.transcription_provider == "openai"


def test_summary_provider_registry_has_named_providers() -> None:
    registry = SummaryProviderRegistry()
    openai = registry.get("openai")
    ollama = registry.get("ollama")
    assert openai.provider_id == "openai"
    assert openai.requires_api_key is True
    assert ollama.provider_id == "ollama"
    assert ollama.is_local is True
    assert ollama.requires_api_key is False
    assert registry.get("xai").provider_id == "xai"
    assert registry.get("anthropic").provider_id == "anthropic"
    assert registry.get("google").provider_id == "google"


@pytest.mark.asyncio
async def test_preflight_keeps_transcription_independent_of_summary_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("WHISPER_LOCAL_USER_ACCESS", raising=False)
    resolver = MagicMock()
    resolver.ensure_model_access = AsyncMock()
    resolver.ensure_user_credential = AsyncMock()
    decision = await ProcessingPreflight(resolver).ensure(
        source_type="media",
        user_id="u1",
        model=ModelType.DEEPSEEK_FLASH,
        user_credits=5,
        transcription_provider="google",
        transcription_model="gemini-3.5-transcribe",
    )
    assert decision.transcription_provider == "google"
    assert decision.transcription_model == "gemini-3.5-transcribe"
    resolver.ensure_model_access.assert_awaited()
    resolver.ensure_user_credential.assert_awaited_once_with("u1", "google")
