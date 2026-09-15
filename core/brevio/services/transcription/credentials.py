from __future__ import annotations

from typing import Optional

from core.brevio.services.transcription.errors import TranscriptionError
from core.brevio_api.models.errors.api_codes import ApiErrorCode
from core.brevio_api.models.errors.provider_errors import (
    ProviderError,
    ProviderErrorKind,
)


async def resolve_paid_transcription_credential(
    resolver, user_id: Optional[str], provider: str
):
    if not user_id:
        raise TranscriptionError(ApiErrorCode.TRANSCRIPTION_API_KEY_REQUIRED)
    if resolver is None:
        raise TranscriptionError(ApiErrorCode.TRANSCRIPTION_API_KEY_REQUIRED)
    try:
        return await resolver.resolve_user_credential(user_id, provider)
    except ProviderError as exc:
        if exc.kind in {
            ProviderErrorKind.USER_CREDENTIAL_REQUIRED,
            ProviderErrorKind.CREDENTIAL_UNAVAILABLE,
            ProviderErrorKind.PLATFORM_CREDENTIAL_UNAVAILABLE,
        }:
            raise TranscriptionError(
                ApiErrorCode.TRANSCRIPTION_API_KEY_REQUIRED
            ) from exc
        if exc.kind in {
            ProviderErrorKind.INVALID_CREDENTIAL,
            ProviderErrorKind.UNAUTHORIZED,
        }:
            raise TranscriptionError(
                ApiErrorCode.TRANSCRIPTION_API_KEY_INVALID
            ) from exc
        raise TranscriptionError(ApiErrorCode.TRANSCRIPTION_FAILED) from exc
