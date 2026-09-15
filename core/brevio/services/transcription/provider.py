from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable

from core.brevio.enums.language import LanguageType
from core.brevio.enums.transcription_provider import TranscriptionProviderType


@dataclass(frozen=True)
class TranscriptionSegment:
    start: float
    text: str


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    segments: list[TranscriptionSegment] = field(default_factory=list)
    language: Optional[str] = None
    duration: Optional[float] = None
    words: list[dict] = field(default_factory=list)
    speakers: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@runtime_checkable
class TranscriptionProvider(Protocol):
    provider_id: TranscriptionProviderType
    requires_api_key: bool

    async def transcribe(
        self,
        audio_path: str,
        language: LanguageType,
        *,
        user_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> TranscriptionResult:
        ...
