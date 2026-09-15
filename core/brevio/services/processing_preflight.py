from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.brevio.enums.transcription_provider import TranscriptionProviderType
from core.brevio.services.credential_resolver import CredentialResolver
from core.brevio.services.summary_providers.access_policy import SummaryAccessPolicy
from core.brevio.services.transcription.catalog import (
    resolve_media_provider,
    resolve_transcription_model,
)
from core.brevio.services.transcription.errors import TranscriptionError
from core.brevio_api.models.errors.api_codes import ApiErrorCode
from core.brevio_api.models.errors.provider_errors import (
    ProviderError,
    ProviderErrorKind,
)
from core.shared.enums.model import ModelType


@dataclass(frozen=True)
class PreflightDecision:
    source_type: str
    model: ModelType
    transcription_provider: Optional[str]
    transcription_model: Optional[str]
    needs_transcription: bool


class ProcessingPreflight:
    """Fail closed before enqueueing paid work or acquiring media."""

    def __init__(
        self,
        resolver: CredentialResolver,
        summary_policy: Optional[SummaryAccessPolicy] = None,
    ) -> None:
        self._resolver = resolver
        self._summary_policy = summary_policy or SummaryAccessPolicy()

    async def ensure(
        self,
        *,
        source_type: str,
        user_id: str,
        model: ModelType,
        user_credits: float = 0,
        transcription_provider: Optional[str] = None,
        transcription_model: Optional[str] = None,
    ) -> PreflightDecision:
        needs_transcription = source_type in {"media", "youtube"}
        self._summary_policy.ensure_user_may_select(model)
        await self._resolver.ensure_model_access(
            user_id, model, user_credits=user_credits
        )
        selected: Optional[str] = None
        selected_model: Optional[str] = None
        if needs_transcription:
            selected, selected_model = await self.ensure_transcription_access(
                user_id, transcription_provider, transcription_model
            )
        return PreflightDecision(
            source_type=source_type,
            model=model,
            transcription_provider=selected,
            transcription_model=selected_model,
            needs_transcription=needs_transcription,
        )

    async def ensure_transcription_access(
        self,
        user_id: str,
        requested: Optional[str],
        requested_model: Optional[str] = None,
    ) -> tuple[str, str]:
        provider = resolve_media_provider(requested)
        model_entry = resolve_transcription_model(provider, requested_model)
        if provider is not TranscriptionProviderType.LOCAL_WHISPER:
            ensure = getattr(self._resolver, "ensure_user_credential", None)
            if callable(ensure):
                try:
                    await ensure(user_id, provider.value)
                except ProviderError as exc:
                    if exc.kind == ProviderErrorKind.USER_CREDENTIAL_REQUIRED:
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
                    raise
        return provider.value, model_entry.id
