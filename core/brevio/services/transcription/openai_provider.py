from __future__ import annotations

import asyncio
import logging
import os
from io import BytesIO
from pathlib import Path
from typing import Optional

from openai import (
    APIError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)

from core.brevio.enums.language import LanguageType
from core.brevio.enums.transcription_provider import TranscriptionProviderType
from core.brevio.services.transcription.credentials import (
    resolve_paid_transcription_credential,
)
from core.brevio.services.transcription.errors import TranscriptionError
from core.brevio.services.transcription.formatting import (
    segments_from_payload,
    whisper_language_code,
)
from core.brevio.services.transcription.models import default_transcription_model
from core.brevio.services.transcription.provider import TranscriptionResult
from core.brevio.services.transcription.redact import redact_secrets
from core.brevio_api.models.errors.api_codes import ApiErrorCode

logger = logging.getLogger(__name__)

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
GPT_TRANSCRIBE = "gpt-transcribe"
WHISPER_1 = "whisper-1"


class OpenAITranscriptionProvider:
    provider_id = TranscriptionProviderType.OPENAI
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
            self._credential_resolver, user_id, "openai"
        )
        vendor_model = (
            model or default_transcription_model(self.provider_id).id
        ).strip()
        api_key = cred.api_key
        base_url = os.getenv("OPENAI_TRANSCRIPTION_API_URL") or DEFAULT_OPENAI_BASE_URL
        timeout = float(os.getenv("OPENAI_TRANSCRIPTION_TIMEOUT", "120"))
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        try:
            audio_bytes = await asyncio.to_thread(Path(audio_path).read_bytes)
            buffer = BytesIO(audio_bytes)
            buffer.name = Path(audio_path).name
            kwargs: dict = {
                "model": vendor_model,
                "file": buffer,
            }
            code = whisper_language_code(language)
            if vendor_model == WHISPER_1:
                kwargs["response_format"] = "verbose_json"
                if code:
                    kwargs["language"] = code
            elif vendor_model == GPT_TRANSCRIBE:
                if code:
                    kwargs["languages"] = [code]
            payload = await asyncio.wait_for(
                client.audio.transcriptions.create(**kwargs),
                timeout=timeout,
            )
        except asyncio.TimeoutError as exc:
            raise TranscriptionError(ApiErrorCode.TRANSCRIPTION_OPENAI_TIMEOUT) from exc
        except APITimeoutError as exc:
            raise TranscriptionError(ApiErrorCode.TRANSCRIPTION_OPENAI_TIMEOUT) from exc
        except AuthenticationError as exc:
            raise TranscriptionError(
                ApiErrorCode.TRANSCRIPTION_API_KEY_INVALID
            ) from exc
        except RateLimitError as exc:
            raise TranscriptionError(ApiErrorCode.TRANSCRIPTION_QUOTA_EXCEEDED) from exc
        except APIError as exc:
            logger.error("OpenAI transcription API error: %s", redact_secrets(str(exc)))
            raise TranscriptionError(ApiErrorCode.TRANSCRIPTION_OPENAI_ERROR) from exc
        except TranscriptionError:
            raise
        except Exception as exc:
            logger.error(
                "OpenAI transcription failed: %s",
                redact_secrets(str(exc)),
                exc_info=True,
            )
            raise TranscriptionError(ApiErrorCode.TRANSCRIPTION_OPENAI_ERROR) from exc
        finally:
            try:
                await client.close()
            except Exception:
                pass

        data = payload
        if hasattr(payload, "model_dump"):
            data = payload.model_dump()
        elif not isinstance(payload, dict):
            data = {
                "text": getattr(payload, "text", "") or "",
                "segments": [
                    {
                        "start": getattr(item, "start", 0.0),
                        "text": getattr(item, "text", ""),
                    }
                    for item in (getattr(payload, "segments", None) or [])
                ],
                "language": getattr(payload, "language", None),
            }
        payload_dict = data if isinstance(data, dict) else {}
        segments = segments_from_payload(payload_dict)
        text = str(payload_dict.get("text") or "")
        detected = payload_dict.get("language")
        languages = payload_dict.get("languages")
        if not detected and isinstance(languages, list) and languages:
            first = languages[0]
            if isinstance(first, dict):
                detected = first.get("code")
            else:
                detected = first
        return TranscriptionResult(
            text=text,
            segments=segments,
            language=str(detected) if detected else None,
            metadata={"vendor_model": vendor_model},
        )
