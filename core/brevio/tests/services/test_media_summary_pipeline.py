from __future__ import annotations

import shutil
import subprocess
import wave
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.brevio.constants.constants import Constants
from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.style import StyleType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.models.file_config_model import FileConfig
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio.models.response_model import SummaryResponse
from core.brevio.services.summary_pipeline import PipelineDocumentError
from core.brevio.services.summary_service import SummaryService
from core.brevio.services.transcription.errors import TranscriptionError
from core.brevio_api.models.errors.api_codes import ApiErrorCode
from core.shared.enums.job_status import JobPhase, JobStatus
from core.shared.enums.model import ModelType
from core.shared.models.brevio.brevio_generate import BrevioGenerate, MediaEntry
from core.shared.models.user.data_result import DataResult


def _ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def _write_silence_wav(path: Path, seconds: float = 0.2, rate: int = 16000) -> None:
    frames = int(rate * seconds)
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\x00\x00" * frames)


def _make_mp4(path: Path) -> None:
    wav = path.with_suffix(".wav")
    _write_silence_wav(wav)
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
            str(path),
        ],
        check=True,
        capture_output=True,
    )


@pytest.fixture(autouse=True)
def mock_db(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "core.brevio_api.core.database.AsyncDB.database", lambda self: MagicMock()
    )


def _prompt() -> PromptConfig:
    return PromptConfig(
        model=ModelType.GPT_4O_MINI,
        category=CategoryType.SIMPLE_SUMMARY.value,
        style=StyleType.SIMPLE_SUMMARY_DEFAULT.value,
        format=OutputFormatType.MARKDOWN,
        language=LanguageType.ENGLISH,
        summary_level=SummaryLevel.CONCISE,
    )


@pytest.mark.asyncio
async def test_transcription_txt_enters_document_pipeline(tmp_path: Path) -> None:
    source = tmp_path / Constants.TRANSCRIPTION_FILE
    source.write_text(
        "[00:00:00] Economics lecture about supply and demand.\n", encoding="utf-8"
    )
    summary_path = tmp_path / Constants.SUMMARY_FILE
    service = SummaryService()
    service.token_bucket = 1_000_000
    file_config = FileConfig(
        transcription_path=str(source),
        document_path=str(source),
        summary_path=str(summary_path),
    )
    with patch.object(
        service.api_service, "check_api_connectivity", new=AsyncMock(return_value=True)
    ), patch.object(
        service.api_service,
        "_initialize_client",
        new=AsyncMock(return_value=MagicMock()),
    ), patch.object(
        service, "detect_language_with_retry_safe", new=AsyncMock(return_value="en")
    ), patch.object(
        service,
        "run_direct_summary",
        new=AsyncMock(return_value=("# Summary\n\nSupply and demand.", 10)),
    ), patch.object(
        service.advanced_prompt_generator,
        "generate_prompt",
        new=AsyncMock(return_value="prompt"),
    ), patch.object(
        service.advanced_prompt_generator,
        "get_direct_summary_prompt",
        new=AsyncMock(return_value="direct"),
    ), patch(
        "core.brevio.services.summary_service.save_log_to_json", new=AsyncMock()
    ):
        result = await service._process_single_document(
            "prompt",
            file_config,
            ModelType.GPT_4O_MINI,
            _prompt(),
            folder_id="folder",
            user_id="user",
        )
    assert result.success is True
    assert summary_path.exists()
    assert "Supply and demand" in summary_path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_process_video_mp4_whisper_then_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from core.brevio.generate import Generate

    monkeypatch.chdir(tmp_path)
    user_folder = "userfolder"
    entry = "entryid"
    dest = tmp_path / "data" / user_folder / entry / "0"
    dest.mkdir(parents=True)
    stored = dest / "lecture.mp4"
    stored.write_bytes(b"fake-mp4")

    generate = Generate()
    generate._transcription_service = MagicMock()
    generate._transcription_service.generate_transcription = AsyncMock(
        return_value="[00:00:00] Hello from whisper"
    )
    generate._summary_service = MagicMock()
    generate._summary_service._process_single_transcription = AsyncMock(
        return_value=SummaryResponse(
            success=True, summary="# Hello", job_phase="COMPLETED"
        )
    )
    generate._verify_file_exists = AsyncMock(return_value=True)

    created: list[DataResult] = []

    async def create_result(user_id: str, folder_id: str, result: DataResult) -> None:
        created.append(result.model_copy(deep=True))

    data = BrevioGenerate(
        data=[MediaEntry(path=stored)],
        prompt_config=_prompt(),
        transcription_provider="local_whisper",
    )
    with patch("core.brevio.generate._empty_cuda_cache", MagicMock()):
        (dest / Constants.TRANSCRIPTION_FILE).write_text("hello", encoding="utf-8")
        result = await generate.process_video(
            0,
            data.data[0],
            data,
            create_result,
            entry,
            user_folder,
            "user-1",
        )
    generate._transcription_service.generate_transcription.assert_awaited()
    kwargs = generate._transcription_service.generate_transcription.await_args.kwargs
    assert kwargs["provider"] == "local_whisper"
    assert kwargs["user_id"] == "user-1"
    assert kwargs["enforce_user_access"] is True
    assert "api_key" not in kwargs
    generate._summary_service._process_single_transcription.assert_awaited()
    file_config = (
        generate._summary_service._process_single_transcription.await_args.kwargs[
            "file_config"
        ]
    )
    assert file_config.transcription_path.endswith(Constants.TRANSCRIPTION_FILE)
    assert file_config.document_path == file_config.transcription_path
    assert result["transcription"]
    assert created[-1].status == JobStatus.COMPLETED.value
    assert created[-1].download_location.startswith("data/")


@pytest.mark.asyncio
async def test_transcription_failure_is_distinct_from_summary_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from core.brevio.generate import Generate

    monkeypatch.chdir(tmp_path)
    dest = tmp_path / "data" / "userfolder" / "entryid" / "0"
    dest.mkdir(parents=True)
    stored = dest / "talk.mp3"
    stored.write_bytes(b"id3")

    generate = Generate()
    generate._transcription_service = MagicMock()
    generate._transcription_service.generate_transcription = AsyncMock(
        side_effect=TranscriptionError(ApiErrorCode.TRANSCRIPTION_LOCAL_WHISPER_ERROR)
    )
    generate._summary_service = MagicMock()
    generate._verify_file_exists = AsyncMock(return_value=True)

    created: list[DataResult] = []

    async def create_result(user_id: str, folder_id: str, result: DataResult) -> None:
        created.append(result.model_copy(deep=True))

    data = BrevioGenerate(
        data=[MediaEntry(path=stored)],
        prompt_config=_prompt(),
        transcription_provider="local_whisper",
    )
    with pytest.raises(TranscriptionError):
        await generate.process_video(
            0, data.data[0], data, create_result, "entryid", "userfolder", "user-1"
        )
    failed = created[-1]
    assert failed.status == JobStatus.FAILED.value
    assert failed.phase == JobPhase.TRANSCRIBING.value
    assert failed.error_code == ApiErrorCode.TRANSCRIPTION_LOCAL_WHISPER_ERROR.value
    generate._summary_service._process_single_transcription.assert_not_called()

    generate._transcription_service.generate_transcription = AsyncMock(
        return_value="ok"
    )
    generate._summary_service._process_single_transcription = AsyncMock(
        return_value=SummaryResponse(
            success=False, summary="", job_phase="REDUCE", message="boom"
        )
    )
    created.clear()
    (dest / Constants.TRANSCRIPTION_FILE).write_text("ok", encoding="utf-8")
    with pytest.raises(PipelineDocumentError):
        await generate.process_video(
            0, data.data[0], data, create_result, "entryid", "userfolder", "user-1"
        )
    failed_summary = created[-1]
    assert failed_summary.status == JobStatus.FAILED.value
    assert (
        failed_summary.error_code
        == ApiErrorCode.SUMMARY_AFTER_TRANSCRIPTION_FAILED.value
    )


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg/ffprobe required")
@pytest.mark.asyncio
async def test_mp4_ffmpeg_whisper_then_summary_pipeline(tmp_path: Path) -> None:
    from core.brevio.services.transcription.local_whisper_provider import (
        LocalWhisperTranscriptionProvider,
    )
    from core.brevio.services.transcription_service import TranscriptionService

    mp4 = tmp_path / "lecture.mp4"
    _make_mp4(mp4)
    work = tmp_path / "work"
    work.mkdir()

    TranscriptionService._instance = None
    TranscriptionService._directory_manager_initialized = False
    LocalWhisperTranscriptionProvider._model = None
    mock_model = MagicMock()
    long_text = "empirical science methodology and experimental evidence. " * 80
    mock_model.transcribe.return_value = {
        "text": long_text,
        "segments": [{"start": 0.0, "text": long_text}],
        "language": "en",
    }

    service = TranscriptionService()
    with patch.object(
        LocalWhisperTranscriptionProvider, "_load_model", return_value=mock_model
    ):
        text = await service.generate_transcription(
            str(mp4),
            str(work),
            LanguageType.ENGLISH,
            provider="local_whisper",
            user_id="dev-user",
            skip_if_exists=False,
        )
    transcription_path = work / Constants.TRANSCRIPTION_FILE
    assert transcription_path.exists()
    assert "empirical science" in text
    mock_model.transcribe.assert_called_once()
    audio_arg = mock_model.transcribe.call_args.args[0]
    assert str(audio_arg).endswith(".wav")

    summary_path = work / Constants.SUMMARY_FILE
    summary_service = SummaryService()
    summary_service.token_bucket = 1_000_000
    file_config = FileConfig(
        transcription_path=str(transcription_path),
        document_path=str(transcription_path),
        summary_path=str(summary_path),
    )
    with patch.object(
        summary_service.api_service,
        "check_api_connectivity",
        new=AsyncMock(return_value=True),
    ), patch.object(
        summary_service.api_service,
        "_initialize_client",
        new=AsyncMock(return_value=MagicMock()),
    ), patch.object(
        summary_service,
        "detect_language_with_retry_safe",
        new=AsyncMock(return_value="en"),
    ), patch.object(
        summary_service,
        "run_map_phase",
        new=AsyncMock(return_value=(["map-chunk"], 20)),
    ), patch.object(
        summary_service,
        "run_reduce_phase",
        new=AsyncMock(return_value=("# Summary\n\nEmpirical science.", 12)),
    ), patch.object(
        summary_service,
        "run_formatting_phase",
        new=AsyncMock(return_value=("# Summary\n\nEmpirical science.", 8)),
    ), patch.object(
        summary_service,
        "run_direct_summary",
        new=AsyncMock(return_value=("# Summary\n\nEmpirical science.", 10)),
    ), patch.object(
        summary_service.advanced_prompt_generator,
        "generate_prompt",
        new=AsyncMock(return_value="prompt"),
    ), patch.object(
        summary_service.advanced_prompt_generator,
        "get_direct_summary_prompt",
        new=AsyncMock(return_value="direct"),
    ), patch.object(
        summary_service.advanced_prompt_generator,
        "get_map_prompt",
        new=AsyncMock(return_value="map"),
    ), patch.object(
        summary_service.advanced_prompt_generator,
        "get_reduce_prompt",
        new=AsyncMock(return_value="reduce"),
    ), patch.object(
        summary_service.advanced_prompt_generator,
        "get_format_prompt",
        new=AsyncMock(return_value="format"),
    ), patch(
        "core.brevio.services.summary_service.save_log_to_json", new=AsyncMock()
    ):
        result = await summary_service._process_single_document(
            "prompt",
            file_config,
            ModelType.GPT_4O_MINI,
            PromptConfig(
                model=ModelType.GPT_4O_MINI,
                category=CategoryType.SIMPLE_SUMMARY.value,
                style=StyleType.SIMPLE_SUMMARY_DEFAULT.value,
                format=OutputFormatType.MARKDOWN,
                language=LanguageType.ENGLISH,
                summary_level=SummaryLevel.VERY_DETAILED,
            ),
            folder_id="folder",
            user_id="dev-user",
        )
    assert result.success is True
    assert summary_path.exists()
    assert "Empirical science" in summary_path.read_text(encoding="utf-8")
    TranscriptionService._instance = None
    TranscriptionService._directory_manager_initialized = False
