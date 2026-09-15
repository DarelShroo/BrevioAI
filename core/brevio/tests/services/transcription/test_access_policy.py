from __future__ import annotations

import os
from unittest.mock import patch

from core.brevio.enums.transcription_provider import TranscriptionProviderType
from core.brevio.services.transcription.access_policy import TranscriptionAccessPolicy
from core.brevio.services.transcription.catalog import (
    build_transcription_providers_payload,
    resolve_media_provider,
)
from core.brevio.services.transcription.errors import TranscriptionError
from core.brevio_api.models.errors.api_codes import ApiErrorCode


def test_local_whisper_is_always_implemented() -> None:
    prod = TranscriptionAccessPolicy(environment="production")
    dev = TranscriptionAccessPolicy(environment="development")
    assert prod.is_implemented(TranscriptionProviderType.LOCAL_WHISPER) is True
    assert dev.is_implemented(TranscriptionProviderType.LOCAL_WHISPER) is True
    assert prod.is_implemented(TranscriptionProviderType.OPENAI) is True
    assert prod.is_implemented(TranscriptionProviderType.GOOGLE) is True
    assert prod.is_implemented(TranscriptionProviderType.XAI) is True


def test_production_hides_local_whisper_but_keeps_it_implemented() -> None:
    policy = TranscriptionAccessPolicy(environment="production")
    assert policy.user_can_select(TranscriptionProviderType.LOCAL_WHISPER) is False
    assert policy.user_can_select(TranscriptionProviderType.OPENAI) is True
    assert policy.user_can_select(TranscriptionProviderType.GOOGLE) is True
    assert policy.user_can_select(TranscriptionProviderType.XAI) is True
    payload = build_transcription_providers_payload(policy)
    by_id = {item["id"]: item for item in payload["providers"]}
    assert by_id["local_whisper"]["implemented"] is True
    assert by_id["local_whisper"]["user_access"] is False
    assert "local_whisper" not in payload["selectable"]
    assert payload["default"] == "openai"


def test_development_keeps_restricted_capability_usable() -> None:
    policy = TranscriptionAccessPolicy(environment="development")
    assert policy.user_can_select(TranscriptionProviderType.LOCAL_WHISPER) is True
    provider = resolve_media_provider("local_whisper", policy=policy)
    assert provider is TranscriptionProviderType.LOCAL_WHISPER


def test_test_environment_behaves_like_dev_override() -> None:
    policy = TranscriptionAccessPolicy(environment="test")
    assert policy.is_production() is False
    assert policy.user_can_select(TranscriptionProviderType.LOCAL_WHISPER) is True


@patch.dict(
    os.environ, {"WHISPER_LOCAL_USER_ACCESS": "true", "ENVIRONMENT": "production"}
)
def test_explicit_env_override_can_enable_local_whisper_in_production() -> None:
    policy = TranscriptionAccessPolicy()
    assert policy.user_can_select(TranscriptionProviderType.LOCAL_WHISPER) is True


def test_production_rejects_user_selection_of_local_whisper() -> None:
    policy = TranscriptionAccessPolicy(environment="production")
    try:
        resolve_media_provider("local_whisper", policy=policy)
        raise AssertionError("expected TranscriptionError")
    except TranscriptionError as exc:
        assert exc.code == ApiErrorCode.TRANSCRIPTION_PROVIDER_NOT_ALLOWED.value
    # Implementation remains available for DEV/internal use.
    from core.brevio.services.transcription.local_whisper_provider import (
        LocalWhisperTranscriptionProvider,
    )

    provider = LocalWhisperTranscriptionProvider()
    assert provider.provider_id is TranscriptionProviderType.LOCAL_WHISPER
    assert provider.requires_api_key is False


def test_internal_default_matches_user_default() -> None:
    prod = TranscriptionAccessPolicy(environment="production")
    dev = TranscriptionAccessPolicy(environment="development")
    assert prod.default_internal_provider() is prod.default_media_provider()
    assert prod.default_internal_provider() is TranscriptionProviderType.OPENAI
    assert dev.default_internal_provider() is TranscriptionProviderType.LOCAL_WHISPER
