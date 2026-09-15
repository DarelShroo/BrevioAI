from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

from core.brevio.enums.extension import is_video_extension
from core.brevio.enums.transcription_provider import TranscriptionProviderType
from core.brevio.services.transcription.errors import TranscriptionError
from core.brevio.services.transcription.redact import redact_secrets
from core.brevio_api.models.errors.api_codes import ApiErrorCode

logger = logging.getLogger(__name__)

OPENAI_WHISPER_MAX_BYTES = 24 * 1024 * 1024
DEFAULT_FFMPEG_TIMEOUT = 300


@dataclass
class PreparedAudio:
    path: str
    duration_seconds: float = 0.0
    cleanup_paths: list[str] = field(default_factory=list)


class MediaPreprocessor:
    """Extract and normalize media with a real FFmpeg conversion."""

    def __init__(self, timeout_seconds: Optional[float] = None) -> None:
        self.timeout_seconds = float(
            timeout_seconds
            if timeout_seconds is not None
            else os.getenv("FFMPEG_TIMEOUT", DEFAULT_FFMPEG_TIMEOUT)
        )

    async def prepare(
        self,
        source_path: str,
        work_dir: str,
        provider: TranscriptionProviderType,
    ) -> PreparedAudio:
        source = Path(source_path)
        destination = Path(work_dir)
        if not source.exists():
            raise FileNotFoundError(f"Audio file not found: {source_path}")
        await asyncio.to_thread(destination.mkdir, parents=True, exist_ok=True)

        probe = await self._probe(source)
        duration = self._duration_seconds(probe)
        if is_video_extension(source.suffix) and not self._has_audio_stream(probe):
            raise TranscriptionError(ApiErrorCode.MEDIA_NO_AUDIO_TRACK)

        cleanup: list[str] = []
        if provider is TranscriptionProviderType.LOCAL_WHISPER:
            output = destination / "normalized_audio.wav"
            await self._run_ffmpeg(
                [
                    "-y",
                    "-i",
                    str(source),
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "pcm_s16le",
                    str(output),
                ]
            )
        else:
            output = destination / "normalized_audio.mp3"
            await self._run_ffmpeg(
                [
                    "-y",
                    "-i",
                    str(source),
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "libmp3lame",
                    "-b:a",
                    "64k",
                    str(output),
                ]
            )
        cleanup.append(str(output))

        if (
            provider is TranscriptionProviderType.OPENAI
            and output.exists()
            and output.stat().st_size > OPENAI_WHISPER_MAX_BYTES
        ):
            compressed = destination / "normalized_audio_compact.mp3"
            await self._run_ffmpeg(
                [
                    "-y",
                    "-i",
                    str(output),
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "libmp3lame",
                    "-b:a",
                    "32k",
                    str(compressed),
                ]
            )
            cleanup.append(str(compressed))
            output = compressed

        if not output.exists() or output.stat().st_size == 0:
            raise TranscriptionError(ApiErrorCode.MEDIA_FFMPEG_ERROR)

        return PreparedAudio(
            path=str(output),
            duration_seconds=duration,
            cleanup_paths=cleanup,
        )

    async def cleanup(self, prepared: PreparedAudio) -> None:
        for path in prepared.cleanup_paths:
            try:
                await asyncio.to_thread(os.remove, path)
            except FileNotFoundError:
                continue
            except OSError as exc:
                logger.warning("Failed to remove temp audio %s: %s", path, exc)

    async def _probe(self, source: Path) -> dict:
        self._require_binaries()
        stdout, stderr, returncode = await self._run(
            [
                "ffprobe",
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(source),
            ]
        )
        if returncode != 0:
            raise self._map_probe_error(stderr)
        try:
            return json.loads(stdout or "{}")
        except json.JSONDecodeError as exc:
            logger.error(
                "ffprobe returned invalid JSON: %s", redact_secrets(stdout[:200])
            )
            raise TranscriptionError(ApiErrorCode.MEDIA_FILE_CORRUPT) from exc

    def _has_audio_stream(self, probe: dict) -> bool:
        for stream in probe.get("streams") or []:
            if str(stream.get("codec_type") or "").lower() == "audio":
                return True
        return False

    def _duration_seconds(self, probe: dict) -> float:
        fmt = probe.get("format") or {}
        raw = fmt.get("duration")
        try:
            return float(raw) if raw is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    async def _run_ffmpeg(self, args: Sequence[str]) -> None:
        self._require_binaries()
        _stdout, stderr, returncode = await self._run(["ffmpeg", *args])
        if returncode != 0:
            raise self._map_ffmpeg_error(stderr)

    async def _run(self, command: Sequence[str]) -> tuple[str, str, int]:
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise TranscriptionError(ApiErrorCode.MEDIA_FFMPEG_ERROR) from exc
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.wait()
            raise TranscriptionError(ApiErrorCode.MEDIA_FFMPEG_TIMEOUT) from exc
        stdout = (stdout_b or b"").decode("utf-8", errors="replace")
        stderr = (stderr_b or b"").decode("utf-8", errors="replace")
        if process.returncode != 0:
            logger.error(
                "media command failed code=%s stderr=%s",
                process.returncode,
                redact_secrets(stderr[-800:]),
            )
        return stdout, stderr, int(process.returncode or 0)

    def _require_binaries(self) -> None:
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            raise TranscriptionError(ApiErrorCode.MEDIA_FFMPEG_ERROR)

    def _map_probe_error(self, stderr: str) -> TranscriptionError:
        lowered = (stderr or "").lower()
        if "does not contain any stream" in lowered or "no audio" in lowered:
            return TranscriptionError(ApiErrorCode.MEDIA_NO_AUDIO_TRACK)
        if "invalid data" in lowered or "corrupt" in lowered or "error" in lowered:
            return TranscriptionError(ApiErrorCode.MEDIA_FILE_CORRUPT)
        return TranscriptionError(ApiErrorCode.MEDIA_FFMPEG_ERROR)

    def _map_ffmpeg_error(self, stderr: str) -> TranscriptionError:
        lowered = (stderr or "").lower()
        if (
            "does not contain any stream" in lowered
            or "output file does not contain any stream" in lowered
        ):
            return TranscriptionError(ApiErrorCode.MEDIA_NO_AUDIO_TRACK)
        if "invalid data" in lowered or "corrupt" in lowered:
            return TranscriptionError(ApiErrorCode.MEDIA_FILE_CORRUPT)
        return TranscriptionError(ApiErrorCode.MEDIA_FFMPEG_ERROR)
