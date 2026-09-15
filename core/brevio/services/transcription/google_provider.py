from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

import httpx

from core.brevio.enums.language import LanguageType
from core.brevio.enums.transcription_provider import TranscriptionProviderType
from core.brevio.services.transcription.credentials import (
    resolve_paid_transcription_credential,
)
from core.brevio.services.transcription.errors import TranscriptionError
from core.brevio.services.transcription.provider import TranscriptionResult
from core.brevio.services.transcription.redact import redact_secrets
from core.brevio_api.models.errors.api_codes import ApiErrorCode

logger = logging.getLogger(__name__)

GEMINI_TRANSCRIBE_MODEL = "gemini-3.5-transcribe"
FILES_UPLOAD_URL = "https://generativelanguage.googleapis.com/upload/v1beta/files"
GENERATE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_TRANSCRIBE_MODEL}:generateContent"
)

_MIME_BY_SUFFIX = {
    ".mp3": "audio/mp3",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
}


def _mime_type(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return _MIME_BY_SUFFIX.get(suffix, "audio/mp3")


class GoogleTranscriptionProvider:
    provider_id = TranscriptionProviderType.GOOGLE
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
            self._credential_resolver, user_id, "google"
        )
        vendor_model = (
            model or GEMINI_TRANSCRIBE_MODEL
        ).strip() or GEMINI_TRANSCRIBE_MODEL
        timeout = float(os.getenv("GOOGLE_TRANSCRIPTION_TIMEOUT", "180"))
        mime = _mime_type(audio_path)
        audio_bytes = await asyncio.to_thread(Path(audio_path).read_bytes)
        headers = {"x-goog-api-key": cred.api_key}
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                file_uri = await self._upload_file(
                    client, headers, Path(audio_path).name, mime, audio_bytes
                )
                generate_url = GENERATE_URL
                if vendor_model != GEMINI_TRANSCRIBE_MODEL:
                    generate_url = (
                        "https://generativelanguage.googleapis.com/v1beta/models/"
                        f"{vendor_model}:generateContent"
                    )
                response = await client.post(
                    generate_url,
                    headers={**headers, "Content-Type": "application/json"},
                    json={
                        "contents": [
                            {
                                "parts": [
                                    {
                                        "fileData": {
                                            "fileUri": file_uri,
                                            "mimeType": mime,
                                        }
                                    }
                                ]
                            }
                        ]
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
                "Google transcription failed: %s",
                redact_secrets(str(exc)),
                exc_info=True,
            )
            raise TranscriptionError(ApiErrorCode.TRANSCRIPTION_FAILED) from exc

        text = _candidate_text(body)
        return TranscriptionResult(
            text=text,
            language=None,
            metadata={"vendor_model": vendor_model},
        )

    async def _upload_file(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        display_name: str,
        mime: str,
        data: bytes,
    ) -> str:
        start = await client.post(
            FILES_UPLOAD_URL,
            headers={
                **headers,
                "X-Goog-Upload-Protocol": "resumable",
                "X-Goog-Upload-Command": "start",
                "X-Goog-Upload-Header-Content-Length": str(len(data)),
                "X-Goog-Upload-Header-Content-Type": mime,
                "Content-Type": "application/json",
            },
            json={"file": {"display_name": display_name}},
        )
        start.raise_for_status()
        upload_url = start.headers.get("x-goog-upload-url") or start.headers.get(
            "X-Goog-Upload-URL"
        )
        if not upload_url:
            raise TranscriptionError(ApiErrorCode.TRANSCRIPTION_FAILED)
        uploaded = await client.post(
            upload_url,
            headers={
                "X-Goog-Upload-Command": "upload, finalize",
                "X-Goog-Upload-Offset": "0",
                "Content-Length": str(len(data)),
            },
            content=data,
        )
        uploaded.raise_for_status()
        payload = uploaded.json()
        file_info = payload.get("file") if isinstance(payload, dict) else None
        uri = None
        if isinstance(file_info, dict):
            uri = file_info.get("uri")
        if not uri and isinstance(payload, dict):
            uri = payload.get("uri")
        if not uri:
            raise TranscriptionError(ApiErrorCode.TRANSCRIPTION_FAILED)
        return str(uri)


def _candidate_text(body: dict) -> str:
    candidates = body.get("candidates") or []
    if not candidates:
        return ""
    content = (candidates[0] or {}).get("content") or {}
    parts = content.get("parts") or []
    texts: list[str] = []
    for part in parts:
        if isinstance(part, dict) and part.get("text"):
            texts.append(str(part["text"]))
    return "".join(texts).strip()
