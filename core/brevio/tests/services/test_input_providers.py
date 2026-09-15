from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.brevio.services.input import media_input_provider_for
from core.brevio.services.input.uploaded_media import UploadedMediaInputProvider
from core.brevio.services.input.youtube import YouTubeInputProvider
from core.shared.models.brevio.brevio_generate import MediaEntry


@pytest.mark.asyncio
async def test_uploaded_media_input_copies_file(tmp_path: Path) -> None:
    source = tmp_path / "talk.mp3"
    source.write_bytes(b"id3")
    dest = tmp_path / "out"
    dest.mkdir()
    provider = UploadedMediaInputProvider(str(source))
    acquired = await provider.acquire(dest, 0)
    assert Path(acquired.audio_path).exists()
    assert Path(acquired.audio_path).read_bytes() == b"id3"
    assert acquired.kind == "uploaded_media"
    assert provider.needs_transcription is True


@pytest.mark.asyncio
async def test_youtube_input_downloads_to_index_mp3(tmp_path: Path) -> None:
    yt = MagicMock()
    yt.download = AsyncMock()
    provider = YouTubeInputProvider("https://youtube.com/watch?v=abc", yt)
    dest = tmp_path / "out"
    dest.mkdir()
    acquired = await provider.acquire(dest, 3)
    yt.download.assert_awaited()
    assert acquired.audio_path.endswith("3.mp3")
    assert acquired.kind == "youtube"


def test_factory_selects_provider_from_entry(tmp_path: Path) -> None:
    yt = MagicMock()
    source = tmp_path / "a.mp3"
    source.write_bytes(b"x")
    uploaded = media_input_provider_for(MediaEntry(path=source), yt_service=yt)
    assert isinstance(uploaded, UploadedMediaInputProvider)
    youtube = media_input_provider_for(
        type("V", (), {"url": "https://youtube.com/watch?v=1", "path": None})(),
        yt_service=yt,
    )
    assert isinstance(youtube, YouTubeInputProvider)
