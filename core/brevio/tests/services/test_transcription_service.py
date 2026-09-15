import logging
from unittest.mock import MagicMock, patch

import pytest

from core.brevio.enums.language import LanguageType
from core.brevio.services.transcription_service import TranscriptionService


@pytest.fixture
def caplog(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    caplog.set_level(logging.DEBUG)
    return caplog


@pytest.fixture
def transcription_service() -> TranscriptionService:
    TranscriptionService._instance = None
    TranscriptionService._directory_manager_initialized = False
    return TranscriptionService()


@pytest.mark.asyncio
async def test_singleton_instance(caplog: pytest.LogCaptureFixture) -> None:
    TranscriptionService._instance = None
    service1 = TranscriptionService()
    assert "Creating new instance of TranscriptionService" in caplog.text
    service2 = TranscriptionService()
    assert service1 is service2
    assert "Reusing existing instance of TranscriptionService" in caplog.text


@pytest.mark.asyncio
async def test_init_directory_manager(caplog: pytest.LogCaptureFixture) -> None:
    TranscriptionService._instance = None
    TranscriptionService._directory_manager_initialized = False
    service = TranscriptionService()
    assert hasattr(service, "_directory_manager")
    assert service._directory_manager is not None
    assert "DirectoryManager initialized" in caplog.text
    caplog.clear()
    TranscriptionService()
    assert "DirectoryManager initialized" not in caplog.text


@pytest.mark.asyncio
async def test_validate_paths_success(
    transcription_service: TranscriptionService,
) -> None:
    with patch("core.brevio.services.transcription_service.exists", return_value=True):
        transcription_service._validate_paths(
            "../../data/audio.mp3", "../../data/audios"
        )


@pytest.mark.asyncio
async def test_validate_paths_audio_not_found(
    transcription_service: TranscriptionService, caplog: pytest.LogCaptureFixture
) -> None:
    with patch(
        "core.brevio.services.transcription_service.exists",
        side_effect=[False, True],
    ):
        with pytest.raises(FileNotFoundError) as exc_info:
            transcription_service._validate_paths(
                "/invalid/audio.mp3", "./backend/audios"
            )
        assert "Audio file not found: /invalid/audio.mp3" in str(exc_info.value)
        assert "Audio file not found: /invalid/audio.mp3" in caplog.text


@pytest.mark.asyncio
async def test_validate_paths_destination_not_found(
    transcription_service: TranscriptionService, caplog: pytest.LogCaptureFixture
) -> None:
    with patch(
        "core.brevio.services.transcription_service.exists",
        side_effect=[True, False],
    ):
        with pytest.raises(FileNotFoundError) as exc_info:
            transcription_service._validate_paths(
                "/valid/audio.mp3", "./backend/audios"
            )
        assert "Destination directory not found: ./backend/audios" in str(
            exc_info.value
        )
        assert "Destination directory not found: ./backend/audios" in caplog.text
