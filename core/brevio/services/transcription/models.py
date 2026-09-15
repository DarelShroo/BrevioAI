from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.brevio.enums.transcription_provider import TranscriptionProviderType


@dataclass(frozen=True)
class TranscriptionModelEntry:
    id: str
    provider: TranscriptionProviderType
    vendor_model_id: Optional[str]
    status: str
    recommended: bool
    retirement: Optional[str]
    parameters: tuple[str, ...]
    display_name: str
    requires_api_key: bool


# Official IDs / endpoints only. xAI file STT has no vendor model field.
TRANSCRIPTION_MODELS: tuple[TranscriptionModelEntry, ...] = (
    TranscriptionModelEntry(
        id="gpt-transcribe",
        provider=TranscriptionProviderType.OPENAI,
        vendor_model_id="gpt-transcribe",
        status="stable",
        recommended=True,
        retirement=None,
        parameters=("prompt", "keywords", "languages"),
        display_name="gpt-transcribe",
        requires_api_key=True,
    ),
    TranscriptionModelEntry(
        id="whisper-1",
        provider=TranscriptionProviderType.OPENAI,
        vendor_model_id="whisper-1",
        status="deprecated",
        recommended=False,
        retirement="2027-02-26",
        parameters=("language", "timestamps"),
        display_name="whisper-1",
        requires_api_key=True,
    ),
    TranscriptionModelEntry(
        id="gemini-3.5-transcribe",
        provider=TranscriptionProviderType.GOOGLE,
        vendor_model_id="gemini-3.5-transcribe",
        status="stable",
        recommended=True,
        retirement=None,
        parameters=("language_codes",),
        display_name="gemini-3.5-transcribe",
        requires_api_key=True,
    ),
    TranscriptionModelEntry(
        id="stt",
        provider=TranscriptionProviderType.XAI,
        vendor_model_id=None,
        status="stable",
        recommended=True,
        retirement=None,
        parameters=("language", "format", "keyterm"),
        display_name="Speech to Text",
        requires_api_key=True,
    ),
    TranscriptionModelEntry(
        id="local_whisper",
        provider=TranscriptionProviderType.LOCAL_WHISPER,
        vendor_model_id=None,
        status="stable",
        recommended=True,
        retirement=None,
        parameters=("language",),
        display_name="local_whisper",
        requires_api_key=False,
    ),
)


def transcription_models_for(
    provider: TranscriptionProviderType,
) -> tuple[TranscriptionModelEntry, ...]:
    return tuple(item for item in TRANSCRIPTION_MODELS if item.provider is provider)


def get_transcription_model(model_id: str) -> Optional[TranscriptionModelEntry]:
    needle = model_id.strip().lower()
    for item in TRANSCRIPTION_MODELS:
        if item.id.lower() == needle:
            return item
        if item.vendor_model_id and item.vendor_model_id.lower() == needle:
            return item
    return None


def default_transcription_model(
    provider: TranscriptionProviderType,
) -> TranscriptionModelEntry:
    models = transcription_models_for(provider)
    recommended = [
        item for item in models if item.recommended and item.status != "deprecated"
    ]
    if recommended:
        return recommended[0]
    if models:
        return models[0]
    raise ValueError(f"No transcription models for provider {provider.value}")
