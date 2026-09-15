from __future__ import annotations

import wave
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.brevio.enums.language import LanguageType
from core.brevio.enums.transcription_provider import TranscriptionProviderType
from core.brevio.services.media_preprocessor import MediaPreprocessor, PreparedAudio
from core.brevio.services.transcription.errors import TranscriptionError
from core.brevio.services.transcription.local_whisper_provider import (
    LocalWhisperTranscriptionProvider,
)
from core.brevio.services.transcription.openai_provider import (
    OpenAITranscriptionProvider,
)
from core.brevio.services.transcription.provider import TranscriptionResult
from core.brevio.services.transcription.redact import redact_secrets
from core.brevio.services.transcription_service import TranscriptionService
from core.brevio_api.models.errors.api_codes import ApiErrorCode
from core.brevio_api.models.errors.provider_errors import (
    ProviderError,
    ProviderErrorKind,
)


@pytest.fixture(autouse=True)
def reset_transcription_singleton() -> None:
    TranscriptionService._instance = None
    TranscriptionService._directory_manager_initialized = False
    yield
    TranscriptionService._instance = None
    TranscriptionService._directory_manager_initialized = False


@pytest.mark.asyncio
async def test_local_whisper_provider_formats_segments(tmp_path: Path) -> None:
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"RIFF")
    provider = LocalWhisperTranscriptionProvider()
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {
        "text": "Hola mundo",
        "segments": [{"start": 0.0, "text": "Hola mundo"}],
        "language": "es",
    }
    with patch.object(provider, "_load_model", return_value=mock_model):
        result = await provider.transcribe(
            str(audio), LanguageType.SPANISH, user_id="u1"
        )
    assert result.segments[0].text == "Hola mundo"
    mock_model.transcribe.assert_called_once()
    assert mock_model.transcribe.call_args.kwargs.get("language") == "es"


@pytest.mark.asyncio
async def test_openai_byok_success() -> None:
    resolver = MagicMock()
    cred = MagicMock(api_key="sk-user-secret", is_platform=False)
    resolver.resolve_user_credential = AsyncMock(return_value=cred)
    provider = OpenAITranscriptionProvider(resolver)

    class FakeTranscript:
        text = "hello"
        segments = [MagicMock(start=0.0, text="hello")]
        language = "en"

        def model_dump(self) -> dict:
            return {
                "text": "hello",
                "segments": [{"start": 0.0, "text": "hello"}],
                "language": "en",
            }

    fake_client = MagicMock()
    fake_client.audio.transcriptions.create = AsyncMock(return_value=FakeTranscript())
    fake_client.close = AsyncMock()
    with patch(
        "core.brevio.services.transcription.openai_provider.AsyncOpenAI",
        return_value=fake_client,
    ), patch(
        "core.brevio.services.transcription.openai_provider.Path.read_bytes",
        return_value=b"audio",
    ):
        result = await provider.transcribe(
            "/tmp/a.wav", LanguageType.ENGLISH, user_id="user-1"
        )
    assert result.text == "hello"
    resolver.resolve_user_credential.assert_awaited_once_with("user-1", "openai")
    kwargs = fake_client.audio.transcriptions.create.call_args.kwargs
    assert kwargs["model"] == "gpt-transcribe"
    assert "sk-user-secret" not in str(result)


@pytest.mark.asyncio
async def test_openai_missing_byok() -> None:
    resolver = MagicMock()
    resolver.resolve_user_credential = AsyncMock(
        side_effect=ProviderError(
            kind=ProviderErrorKind.USER_CREDENTIAL_REQUIRED, message="missing"
        )
    )
    provider = OpenAITranscriptionProvider(resolver)
    with pytest.raises(TranscriptionError) as exc:
        await provider.transcribe("/tmp/a.wav", LanguageType.ENGLISH, user_id="user-1")
    assert exc.value.code == ApiErrorCode.TRANSCRIPTION_API_KEY_REQUIRED.value


@pytest.mark.asyncio
async def test_openai_invalid_key() -> None:
    from openai import AuthenticationError

    resolver = MagicMock()
    cred = MagicMock(api_key="sk-bad", is_platform=False)
    resolver.resolve_user_credential = AsyncMock(return_value=cred)
    provider = OpenAITranscriptionProvider(resolver)
    fake_client = MagicMock()
    fake_client.audio.transcriptions.create = AsyncMock(
        side_effect=AuthenticationError(
            "invalid",
            response=MagicMock(status_code=401, headers={}),
            body=None,
        )
    )
    fake_client.close = AsyncMock()
    with patch(
        "core.brevio.services.transcription.openai_provider.AsyncOpenAI",
        return_value=fake_client,
    ), patch(
        "core.brevio.services.transcription.openai_provider.Path.read_bytes",
        return_value=b"audio",
    ), pytest.raises(
        TranscriptionError
    ) as exc:
        await provider.transcribe("/tmp/a.wav", LanguageType.ENGLISH, user_id="user-1")
    assert exc.value.code == ApiErrorCode.TRANSCRIPTION_API_KEY_INVALID.value


@pytest.mark.asyncio
async def test_openai_timeout() -> None:
    resolver = MagicMock()
    cred = MagicMock(api_key="sk-user", is_platform=False)
    resolver.resolve_user_credential = AsyncMock(return_value=cred)
    provider = OpenAITranscriptionProvider(resolver)
    fake_client = MagicMock()
    fake_client.audio.transcriptions.create = AsyncMock(side_effect=TimeoutError())
    fake_client.close = AsyncMock()
    with patch(
        "core.brevio.services.transcription.openai_provider.AsyncOpenAI",
        return_value=fake_client,
    ), patch(
        "core.brevio.services.transcription.openai_provider.Path.read_bytes",
        return_value=b"audio",
    ), pytest.raises(
        TranscriptionError
    ) as exc:
        await provider.transcribe("/tmp/a.wav", LanguageType.ENGLISH, user_id="user-1")
    assert exc.value.code == ApiErrorCode.TRANSCRIPTION_OPENAI_TIMEOUT.value


@pytest.mark.asyncio
async def test_transcription_service_persists_text(tmp_path: Path) -> None:
    audio = tmp_path / "clip.mp3"
    audio.write_bytes(b"id3")
    preprocessor = MagicMock()
    preprocessor.prepare = AsyncMock(
        return_value=PreparedAudio(path=str(audio), cleanup_paths=[])
    )
    preprocessor.cleanup = AsyncMock()
    engine = MagicMock()
    engine.transcribe = AsyncMock(
        return_value=TranscriptionResult(
            text="hola",
            segments=[],
        )
    )
    service = TranscriptionService(
        preprocessor=preprocessor,
        access_policy=None,
    )
    service._access_policy = MagicMock()
    with patch(
        "core.brevio.services.transcription_service.resolve_media_provider",
        return_value=TranscriptionProviderType.LOCAL_WHISPER,
    ), patch.object(service, "_provider_for", return_value=engine):
        text = await service.generate_transcription(
            str(audio),
            str(tmp_path),
            LanguageType.SPANISH,
            provider="local_whisper",
            user_id="user",
            skip_if_exists=False,
        )
    assert "hola" in text
    assert (tmp_path / "transcription.txt").read_text(encoding="utf-8")
    preprocessor.prepare.assert_awaited()
    engine.transcribe.assert_awaited()


def test_redact_secrets_strips_api_keys() -> None:
    leaked = "Authorization Bearer sk-abcdefghijklmnopqrstuvwxyz error"
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in redact_secrets(leaked)
    assert "[REDACTED]" in redact_secrets(leaked)


@pytest.mark.asyncio
async def test_google_transcription_mocked_httpx(tmp_path: Path) -> None:
    from core.brevio.services.transcription.google_provider import (
        GoogleTranscriptionProvider,
    )

    audio = tmp_path / "clip.mp3"
    audio.write_bytes(b"id3")
    resolver = MagicMock()
    cred = MagicMock(api_key="gemini-secret")
    resolver.resolve_user_credential = AsyncMock(return_value=cred)
    provider = GoogleTranscriptionProvider(resolver)

    class FakeResponse:
        def __init__(self, payload=None, headers=None, status_code=200):
            self._payload = payload or {}
            self.headers = headers or {}
            self.status_code = status_code

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise RuntimeError("http error")

        def json(self):
            return self._payload

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, headers=None, json=None, content=None):
            if "upload" in url and json is not None:
                return FakeResponse(
                    headers={"x-goog-upload-url": "https://upload.test/file"}
                )
            if url == "https://upload.test/file":
                return FakeResponse(
                    {
                        "file": {
                            "uri": "https://generativelanguage.googleapis.com/files/abc"
                        }
                    }
                )
            return FakeResponse(
                {
                    "candidates": [
                        {"content": {"parts": [{"text": "transcribed from gemini"}]}}
                    ]
                }
            )

    with patch(
        "core.brevio.services.transcription.google_provider.httpx.AsyncClient",
        return_value=FakeClient(),
    ):
        result = await provider.transcribe(
            str(audio), LanguageType.ENGLISH, user_id="u1"
        )
    assert result.text == "transcribed from gemini"
    resolver.resolve_user_credential.assert_awaited_once_with("u1", "google")


@pytest.mark.asyncio
async def test_xai_transcription_mocked_httpx(tmp_path: Path) -> None:
    from core.brevio.services.transcription.xai_provider import XAITranscriptionProvider

    audio = tmp_path / "clip.mp3"
    audio.write_bytes(b"id3")
    resolver = MagicMock()
    cred = MagicMock(api_key="xai-secret")
    resolver.resolve_user_credential = AsyncMock(return_value=cred)
    provider = XAITranscriptionProvider(resolver)

    class FakeResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {
                "text": "hello from grok",
                "language": "en",
                "duration": 1.2,
                "words": [{"text": "hello", "start": 0.0, "end": 0.4}],
            }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, headers=None, data=None, files=None):
            assert "/stt" in url
            assert "xai-secret" not in str(data)
            return FakeResponse()

    with patch(
        "core.brevio.services.transcription.xai_provider.httpx.AsyncClient",
        return_value=FakeClient(),
    ):
        result = await provider.transcribe(
            str(audio), LanguageType.ENGLISH, user_id="u1"
        )
    assert result.text == "hello from grok"
    assert result.duration == 1.2
    resolver.resolve_user_credential.assert_awaited_once_with("u1", "xai")


@pytest.mark.asyncio
async def test_google_missing_key() -> None:
    from core.brevio.services.transcription.google_provider import (
        GoogleTranscriptionProvider,
    )

    resolver = MagicMock()
    resolver.resolve_user_credential = AsyncMock(
        side_effect=ProviderError(
            kind=ProviderErrorKind.USER_CREDENTIAL_REQUIRED, message="missing"
        )
    )
    provider = GoogleTranscriptionProvider(resolver)
    with pytest.raises(TranscriptionError) as exc:
        await provider.transcribe("/tmp/a.wav", LanguageType.ENGLISH, user_id="user-1")
    assert exc.value.code == ApiErrorCode.TRANSCRIPTION_API_KEY_REQUIRED.value
