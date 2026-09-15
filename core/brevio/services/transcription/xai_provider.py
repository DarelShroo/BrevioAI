from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import httpx

from core.brevio.enums.language import LanguageType
from core.brevio.enums.transcription_provider import TranscriptionProviderType
from core.brevio.services.provider_registry import get_provider_base_url
from core.brevio.services.transcription.credentials import (
    resolve_paid_transcription_credential,
)
from core.brevio.services.transcription.errors import TranscriptionError
from core.brevio.services.transcription.formatting import whisper_language_code
from core.brevio.services.transcription.provider import (
    TranscriptionResult,
    TranscriptionSegment,
)
from core.brevio.services.transcription.redact import redact_secrets
from core.brevio_api.models.errors.api_codes import ApiErrorCode

logger = logging.getLogger(__name__)

_XAI_FORMAT_LANGUAGES = frozenset(
    {
        "ar",
        "cs",
        "da",
        "nl",
        "en",
        "fil",
        "fr",
        "de",
        "hi",
        "id",
        "it",
        "ja",
        "ko",
        "mk",
        "ms",
        "fa",
        "pl",
        "pt",
        "ro",
        "ru",
        "es",
        "sv",
        "th",
        "tr",
        "vi",
    }
)


class XAITranscriptionProvider:
    provider_id = TranscriptionProviderType.XAI
    requires_api_key = True

    def __init__(self, credential_resolver) -> None:
        self._credential_resolver = credential_resolver

    async def transcribe(
        self,
        audio_path: str,
        language: LanguageType,
        *,
        user_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> TranscriptionResult:
        cred = await resolve_paid_transcription_credential(
            self._credential_resolver, user_id, "xai"
        )
        timeout = float(os.getenv("XAI_TRANSCRIPTION_TIMEOUT", "180"))
        base = get_provider_base_url("xai").rstrip("/")
        url = f"{base}/stt"
        code = whisper_language_code(language)
        form: dict[str, str] = {}
        if code and code in _XAI_FORMAT_LANGUAGES:
            form["language"] = code
            form["format"] = "true"
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                with open(audio_path, "rb") as handle:
                    response = await client.post(
                        url,
                        headers={"Authorization": f"Bearer {cred.api_key}"},
                        data=form,
                        files={
                            "file": (
                                Path(audio_path).name,
                                handle,
                                "application/octet-stream",
                            )
                        },
                    )
            if response.status_code in {401, 403}:
                raise TranscriptionError(ApiErrorCode.TRANSCRIPTION_API_KEY_INVALID)
            if response.status_code == 429:
                raise TranscriptionError(ApiErrorCode.TRANSCRIPTION_QUOTA_EXCEEDED)
            response.raise_for_status()
            body = response.json()
        except TranscriptionError:
            raise
        except httpx.TimeoutException as exc:
            raise TranscriptionError(ApiErrorCode.TRANSCRIPTION_TIMEOUT) from exc
        except Exception as exc:
            logger.error(
                "xAI transcription failed: %s",
                redact_secrets(str(exc)),
                exc_info=True,
            )
            raise TranscriptionError(ApiErrorCode.TRANSCRIPTION_FAILED) from exc

        text = str(body.get("text") or "")
        words = body.get("words") if isinstance(body.get("words"), list) else []
        segments: list[TranscriptionSegment] = []
        for item in words:
            if not isinstance(item, dict):
                continue
            word_text = str(item.get("text") or "").strip()
            if not word_text:
                continue
            try:
                start = float(item.get("start") or 0.0)
            except (TypeError, ValueError):
                start = 0.0
            segments.append(TranscriptionSegment(start=start, text=word_text))
        duration = body.get("duration")
        try:
            duration_value = float(duration) if duration is not None else None
        except (TypeError, ValueError):
            duration_value = None
        detected = body.get("language")
        return TranscriptionResult(
            text=text,
            segments=segments,
            language=str(detected) if detected else None,
            duration=duration_value,
            words=[item for item in words if isinstance(item, dict)],
            metadata={"endpoint": "POST /v1/stt"},
        )
