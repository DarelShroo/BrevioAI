from __future__ import annotations

from typing import Optional

from core.brevio.enums.transcription_provider import TranscriptionProviderType
from core.brevio.services.transcription.access_policy import (
    TranscriptionAccessPolicy,
    TranscriptionProviderAccess,
)
from core.brevio.services.transcription.errors import TranscriptionError
from core.brevio.services.transcription.models import (
    TranscriptionModelEntry,
    default_transcription_model,
    get_transcription_model,
    transcription_models_for,
)
from core.brevio_api.models.errors.api_codes import ApiErrorCode

_ALIASES = {
    "openai": TranscriptionProviderType.OPENAI,
    "openai_whisper": TranscriptionProviderType.OPENAI,
    "whisper_api": TranscriptionProviderType.OPENAI,
    "google": TranscriptionProviderType.GOOGLE,
    "gemini": TranscriptionProviderType.GOOGLE,
    "xai": TranscriptionProviderType.XAI,
    "grok": TranscriptionProviderType.XAI,
    "local_whisper": TranscriptionProviderType.LOCAL_WHISPER,
    "whisper_local": TranscriptionProviderType.LOCAL_WHISPER,
    "whisper": TranscriptionProviderType.LOCAL_WHISPER,
    "local": TranscriptionProviderType.LOCAL_WHISPER,
}


def parse_transcription_provider(
    value: str | TranscriptionProviderType,
) -> TranscriptionProviderType:
    if isinstance(value, TranscriptionProviderType):
        return value
    normalized = value.strip().lower().replace("-", "_")
    provider = _ALIASES.get(normalized)
    if provider is None:
        raise TranscriptionError(ApiErrorCode.TRANSCRIPTION_PROVIDER_UNKNOWN)
    return provider


def list_transcription_providers(
    policy: Optional[TranscriptionAccessPolicy] = None,
) -> list[TranscriptionProviderAccess]:
    policy = policy or TranscriptionAccessPolicy()
    return [policy.describe(provider) for provider in TranscriptionProviderType]


def resolve_media_provider(
    requested: Optional[str],
    *,
    policy: Optional[TranscriptionAccessPolicy] = None,
    enforce_user_access: bool = True,
) -> TranscriptionProviderType:
    policy = policy or TranscriptionAccessPolicy()
    if requested is None or str(requested).strip() == "":
        provider = policy.default_media_provider()
    else:
        provider = parse_transcription_provider(requested)
    if enforce_user_access:
        policy.ensure_user_may_select(provider)
    return provider


def resolve_transcription_model(
    provider: TranscriptionProviderType,
    requested: Optional[str] = None,
) -> TranscriptionModelEntry:
    if requested is None or str(requested).strip() == "":
        return default_transcription_model(provider)
    entry = get_transcription_model(requested)
    if entry is None or entry.provider is not provider:
        raise TranscriptionError(ApiErrorCode.TRANSCRIPTION_PROVIDER_UNKNOWN)
    if entry.status == "deprecated" and not entry.recommended:
        # Deprecated models remain selectable until the vendor retirement date.
        return entry
    return entry


def build_transcription_providers_payload(
    policy: Optional[TranscriptionAccessPolicy] = None,
) -> dict:
    policy = policy or TranscriptionAccessPolicy()
    providers = list_transcription_providers(policy)
    models: list[dict] = []
    for provider in TranscriptionProviderType:
        access = policy.user_can_select(provider)
        for item in transcription_models_for(provider):
            models.append(
                {
                    "id": item.id,
                    "provider": item.provider.value,
                    "vendor_model_id": item.vendor_model_id,
                    "status": item.status,
                    "recommended": item.recommended,
                    "retirement": item.retirement,
                    "parameters": list(item.parameters),
                    "display_name": item.display_name,
                    "requires_api_key": item.requires_api_key,
                    "user_access": access,
                }
            )
    selectable_providers = [item.id for item in providers if item.user_access]
    default_provider = (
        policy.default_media_provider() if policy.selectable_providers() else None
    )
    default_model = (
        default_transcription_model(default_provider).id if default_provider else None
    )
    return {
        "environment": policy.environment,
        "providers": [
            {
                "id": item.id,
                "implemented": item.implemented,
                "user_access": item.user_access,
                "requires_api_key": item.requires_api_key,
                "access": item.access,
                "display_name": item.display_name,
            }
            for item in providers
        ],
        "models": models,
        "selectable": selectable_providers,
        "default": default_provider.value if default_provider else None,
        "default_model": default_model,
    }
