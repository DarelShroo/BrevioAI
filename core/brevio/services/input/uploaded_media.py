from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from core.brevio.services.input.provider import AcquiredMedia


class UploadedMediaInputProvider:
    kind = "uploaded_media"
    needs_transcription = True

    def __init__(self, source_path: str) -> None:
        self._source = Path(source_path)

    async def acquire(self, destination: Path, index: int) -> AcquiredMedia:
        del index
        dest_path = destination / self._source.name
        if not await asyncio.to_thread(self._source.exists):
            raise FileNotFoundError(f"Fichero no encontrado: {self._source}")
        if self._source.resolve() != dest_path.resolve():
            await asyncio.to_thread(shutil.copy, self._source, dest_path)
        return AcquiredMedia(audio_path=str(dest_path), kind=self.kind)
