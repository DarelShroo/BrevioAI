from __future__ import annotations

from pathlib import Path

from pydantic import HttpUrl

from core.brevio.services.input.provider import AcquiredMedia
from core.brevio.services.yt_service import YTService


class YouTubeInputProvider:
    kind = "youtube"
    needs_transcription = True

    def __init__(self, url: str, yt_service: YTService) -> None:
        self._url = url
        self._yt_service = yt_service

    async def acquire(self, destination: Path, index: int) -> AcquiredMedia:
        await self._yt_service.download(
            HttpUrl(self._url), str(destination), str(index)
        )
        return AcquiredMedia(
            audio_path=str(destination / f"{index}.mp3"),
            kind=self.kind,
        )
