from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from core.brevio.enums.transcription_provider import TranscriptionProviderType
from core.brevio.services.transcription.errors import TranscriptionError
from core.brevio_api.models.errors.api_codes import ApiErrorCode
from core.shared.utils.environment import (
    current_environment,
    is_production_environment,
    local_user_access,
    parse_enabled_ids,
)

_OPENAI_ALIASES = frozenset({"openai", "openai_whisper", "whisper_api"})
_GOOGLE_ALIASES = frozenset({"google", "gemini"})
_XAI_ALIASES = frozenset({"xai", "grok"})
_LOCAL_ALIASES = frozenset({"local_whisper", "whisper_local", "whisper", "local"})


def _enabled_transcription_providers() -> Optional[frozenset[str]]:
    enabled = parse_enabled_ids("ENABLED_TRANSCRIPTION_PROVIDERS")
    if enabled is None:
        return None
    allowed: set[str] = set()
    for token in enabled:
        if token in _OPENAI_ALIASES:
            allowed.add(TranscriptionProviderType.OPENAI.value)
        elif token in _GOOGLE_ALIASES:
            allowed.add(TranscriptionProviderType.GOOGLE.value)
        elif token in _XAI_ALIASES:
            allowed.add(TranscriptionProviderType.XAI.value)
        elif token in _LOCAL_ALIASES:
            allowed.add(TranscriptionProviderType.LOCAL_WHISPER.value)
        else:
            allowed.add(token)
    return frozenset(allowed)


@dataclass(frozen=True)
class TranscriptionProviderAccess:
    id: str
    implemented: bool
    user_access: bool
    requires_api_key: bool
    access: str
    display_name: str


class TranscriptionAccessPolicy:
    """Separates technical capability from end-user availability.

    Local Whisper is always implemented. Production hides it from end users.
    Development (and any non-production environment, including tests) keeps
    it selectable so developers can exercise the real provider.
    """

    def __init__(self, environment: Optional[str] = None) -> None:
        self._environment_override = environment

    @property
    def environment(self) -> str:
        if self._environment_override is not None:
            return self._environment_override.strip().lower() or current_environment()
        return current_environment()

    def is_production(self) -> bool:
        return is_production_environment(self.environment)

    def is_implemented(self, provider: TranscriptionProviderType) -> bool:
        return provider in {
            TranscriptionProviderType.OPENAI,
            TranscriptionProviderType.GOOGLE,
            TranscriptionProviderType.XAI,
            TranscriptionProviderType.LOCAL_WHISPER,
        }

    def user_can_select(self, provider: TranscriptionProviderType) -> bool:
        if not self.is_implemented(provider):
            return False
        enabled = _enabled_transcription_providers()
        if enabled is not None and provider.value not in enabled:
            return False
        if provider is TranscriptionProviderType.LOCAL_WHISPER:
            return local_user_access(
                "WHISPER_LOCAL_USER_ACCESS", environment=self.environment
            )
        return True

    def describe(
        self, provider: TranscriptionProviderType
    ) -> TranscriptionProviderAccess:
        requires_key = provider is not TranscriptionProviderType.LOCAL_WHISPER
        return TranscriptionProviderAccess(
            id=provider.value,
            implemented=self.is_implemented(provider),
            user_access=self.user_can_select(provider),
            requires_api_key=requires_key,
            access="pay_per_use" if requires_key else "local",
            display_name=provider.value,
        )

    def ensure_user_may_select(self, provider: TranscriptionProviderType) -> None:
        if not self.is_implemented(provider):
            raise TranscriptionError(ApiErrorCode.TRANSCRIPTION_PROVIDER_UNKNOWN)
        if not self.user_can_select(provider):
            raise TranscriptionError(ApiErrorCode.TRANSCRIPTION_PROVIDER_NOT_ALLOWED)

    def selectable_providers(self) -> list[TranscriptionProviderType]:
        return [
            provider
            for provider in TranscriptionProviderType
            if self.user_can_select(provider)
        ]

    def default_media_provider(self) -> TranscriptionProviderType:
        selectable = self.selectable_providers()
        if not selectable:
            raise TranscriptionError(ApiErrorCode.TRANSCRIPTION_PROVIDER_NOT_ALLOWED)
        requested = os.getenv("TRANSCRIPTION_DEFAULT_PROVIDER")
        if requested and requested.strip():
            from core.brevio.services.transcription.catalog import (
                parse_transcription_provider,
            )

            try:
                parsed = parse_transcription_provider(requested)
                if parsed in selectable:
                    return parsed
            except TranscriptionError:
                pass
        if (
            not self.is_production()
            and TranscriptionProviderType.LOCAL_WHISPER in selectable
        ):
            return TranscriptionProviderType.LOCAL_WHISPER
        if TranscriptionProviderType.OPENAI in selectable:
            return TranscriptionProviderType.OPENAI
        return selectable[0]

    def default_internal_provider(self) -> TranscriptionProviderType:
        """Same default as user selection. YouTube cannot bypass production policy."""
        return self.default_media_provider()
