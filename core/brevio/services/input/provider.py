from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class AcquiredMedia:
    audio_path: str
    kind: str


@runtime_checkable
class MediaInputProvider(Protocol):
    kind: str
    needs_transcription: bool

    async def acquire(self, destination: Path, index: int) -> AcquiredMedia:
        ...
