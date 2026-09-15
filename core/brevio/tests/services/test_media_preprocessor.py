from __future__ import annotations

import json
import shutil
import struct
import wave
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.brevio.enums.language import LanguageType
from core.brevio.enums.transcription_provider import TranscriptionProviderType
from core.brevio.services.media_preprocessor import MediaPreprocessor
from core.brevio.services.transcription.errors import TranscriptionError
from core.brevio_api.models.errors.api_codes import ApiErrorCode


def _write_silence_wav(path: Path, seconds: float = 0.2, rate: int = 16000) -> None:
    frames = int(rate * seconds)
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\x00\x00" * frames)


def _ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg/ffprobe required")
@pytest.mark.asyncio
async def test_wav_normalization(tmp_path: Path) -> None:
    source = tmp_path / "clip.wav"
    _write_silence_wav(source)
    prepared = await MediaPreprocessor(timeout_seconds=30).prepare(
        str(source), str(tmp_path / "work"), TranscriptionProviderType.LOCAL_WHISPER
    )
    assert Path(prepared.path).exists()
    assert prepared.path.endswith(".wav")
    await MediaPreprocessor().cleanup(prepared)
    assert not Path(prepared.path).exists()


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg/ffprobe required")
@pytest.mark.asyncio
async def test_mp4_goes_through_ffmpeg(tmp_path: Path) -> None:
    wav = tmp_path / "speech.wav"
    _write_silence_wav(wav)
    mp4 = tmp_path / "clip.mp4"
    import subprocess

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=160x120:d=0.2",
            "-i",
            str(wav),
            "-shortest",
            "-c:v",
            "mpeg4",
            "-c:a",
            "aac",
            str(mp4),
        ],
        check=True,
        capture_output=True,
    )
    preprocessor = MediaPreprocessor(timeout_seconds=30)
    prepared = await preprocessor.prepare(
        str(mp4), str(tmp_path / "work"), TranscriptionProviderType.LOCAL_WHISPER
    )
    assert Path(prepared.path).suffix == ".wav"
    await preprocessor.cleanup(prepared)


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg/ffprobe required")
@pytest.mark.asyncio
async def test_video_without_audio_is_rejected(tmp_path: Path) -> None:
    mp4 = tmp_path / "silent.mp4"
    import subprocess

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=160x120:d=0.2",
            "-c:v",
            "mpeg4",
            str(mp4),
        ],
        check=True,
        capture_output=True,
    )
    with pytest.raises(TranscriptionError) as exc:
        await MediaPreprocessor(timeout_seconds=30).prepare(
            str(mp4), str(tmp_path / "work"), TranscriptionProviderType.LOCAL_WHISPER
        )
    assert exc.value.code == ApiErrorCode.MEDIA_NO_AUDIO_TRACK.value


@pytest.mark.asyncio
async def test_corrupt_file_maps_to_business_error(tmp_path: Path) -> None:
    broken = tmp_path / "broken.mp3"
    broken.write_bytes(b"not-an-audio-file")
    preprocessor = MediaPreprocessor(timeout_seconds=5)
    if not _ffmpeg_available():
        preprocessor._run = AsyncMock(return_value=("{}", "Invalid data found", 1))  # type: ignore[method-assign]
        with pytest.raises(TranscriptionError) as exc:
            await preprocessor.prepare(
                str(broken), str(tmp_path / "work"), TranscriptionProviderType.OPENAI
            )
        assert exc.value.code in {
            ApiErrorCode.MEDIA_FILE_CORRUPT.value,
            ApiErrorCode.MEDIA_FFMPEG_ERROR.value,
        }
        return
    with pytest.raises(TranscriptionError) as exc:
        await preprocessor.prepare(
            str(broken), str(tmp_path / "work"), TranscriptionProviderType.OPENAI
        )
    assert exc.value.code in {
        ApiErrorCode.MEDIA_FILE_CORRUPT.value,
        ApiErrorCode.MEDIA_FFMPEG_ERROR.value,
    }
