from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import Any, Optional

from core.brevio.enums.language import LanguageType
from core.brevio.enums.transcription_provider import TranscriptionProviderType
from core.brevio.services.transcription.errors import TranscriptionError
from core.brevio.services.transcription.formatting import (
    segments_from_payload,
    whisper_language_code,
)
from core.brevio.services.transcription.provider import TranscriptionResult
from core.brevio.services.transcription.redact import redact_secrets
from core.brevio_api.models.errors.api_codes import ApiErrorCode

logger = logging.getLogger(__name__)


class LocalWhisperTranscriptionProvider:
    provider_id = TranscriptionProviderType.LOCAL_WHISPER
    requires_api_key = False

    _model: Any = None
    _model_name: Optional[str] = None
    _lock = threading.Lock()

    def _load_model(self) -> Any:
        try:
            import whisper
        except ImportError as exc:
            logger.error(
                "Local Whisper requested but openai-whisper/torch are not installed. "
                "Install core/requirements.dev.txt for local transcription."
            )
            raise TranscriptionError(
                ApiErrorCode.TRANSCRIPTION_LOCAL_WHISPER_ERROR
            ) from exc

        name = os.getenv("WHISPER_LOCAL_MODEL", "small")
        with self._lock:
            if self._model is None or self._model_name != name:
                logger.info("Loading local Whisper model %s", name)
                self._model = whisper.load_model(name)
                self._model_name = name
            return self._model

    async def transcribe(
        self,
        audio_path: str,
        language: LanguageType,
        *,
        user_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> TranscriptionResult:
        del user_id, model
        timeout = float(os.getenv("WHISPER_LOCAL_TIMEOUT", "600"))
        try:
            model = await asyncio.to_thread(self._load_model)
            kwargs: dict[str, Any] = {}
            code = whisper_language_code(language)
            if code:
                kwargs["language"] = code
            loop = asyncio.get_running_loop()
            payload = await asyncio.wait_for(
                loop.run_in_executor(
                    None, lambda: model.transcribe(audio_path, **kwargs)
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError as exc:
            raise TranscriptionError(ApiErrorCode.TRANSCRIPTION_TIMEOUT) from exc
        except TranscriptionError:
            raise
        except Exception as exc:
            logger.error(
                "Local Whisper failed: %s",
                redact_secrets(str(exc)),
                exc_info=True,
            )
            raise TranscriptionError(
                ApiErrorCode.TRANSCRIPTION_LOCAL_WHISPER_ERROR
            ) from exc

        segments = segments_from_payload(payload if isinstance(payload, dict) else {})
        text = str((payload or {}).get("text") or "")
        detected = (payload or {}).get("language")
        return TranscriptionResult(
            text=text,
            segments=segments,
            language=str(detected) if detected else whisper_language_code(language),
        )
