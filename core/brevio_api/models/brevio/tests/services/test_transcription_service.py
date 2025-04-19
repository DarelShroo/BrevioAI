import logging
from typing import Any, Awaitable, Dict, List, Union
from unittest.mock import MagicMock, Mock, patch

import pytest

from core.brevio.constants.constants import Constants
from core.brevio.enums.language import LanguageType
from core.brevio.services.transcription_service import TranscriptionService


@pytest.fixture
def caplog(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    """Should set the logging level to DEBUG for transcription service tests."""
    caplog.set_level(logging.DEBUG)
    return caplog


@pytest.fixture
def transcription_service() -> TranscriptionService:
    """Should provide a fresh instance of TranscriptionService for testing by resetting the singleton."""
    TranscriptionService._instance = None
    return TranscriptionService()


@pytest.mark.asyncio
async def test_singleton_instance(caplog: pytest.LogCaptureFixture) -> None:
    """Test that TranscriptionService follows the singleton pattern."""
    # Reset singleton for test
    TranscriptionService._instance = None

    # Create first instance
    service1 = TranscriptionService()
    assert "Creating new instance of TranscriptionService" in caplog.text

    # Create second instance
    service2 = TranscriptionService()
    assert service1 is service2
    assert "Reusing existing instance of TranscriptionService" in caplog.text


@pytest.mark.asyncio
async def test_init_directory_manager(caplog: pytest.LogCaptureFixture) -> None:
    """Test that directory manager is properly initialized."""
    # Reset singleton and directory manager initialization flag for test
    TranscriptionService._instance = None
    TranscriptionService._directory_manager_initialized = False

    # Create first instance
    service = TranscriptionService()
    assert hasattr(service, "_directory_manager")
    assert service._directory_manager is not None
    assert "DirectoryManager initialized" in caplog.text

    # Create second instance
    caplog.clear()
    service2 = TranscriptionService()
    # DirectoryManager should not be initialized again
    assert "DirectoryManager initialized" not in caplog.text


@pytest.mark.asyncio
async def test_validate_paths_success(
    transcription_service: TranscriptionService,
) -> None:
    """Should not raise any errors when valid paths are provided."""
    with patch("core.brevio.services.transcription_service.exists", return_value=True):
        transcription_service._validate_paths(
            "../../data/audio.mp3", "../../data/audios"
        )


@pytest.mark.asyncio
async def test_validate_paths_audio_not_found(
    transcription_service: TranscriptionService, caplog: pytest.LogCaptureFixture
) -> None:
    """Should raise FileNotFoundError when the audio file is not found."""
    with patch(
        "core.brevio.services.transcription_service.exists",
        side_effect=[False, True],
    ):
        with pytest.raises(FileNotFoundError) as exc_info:
            transcription_service._validate_paths(
                "/invalid/audio.mp3", "./backend/audios"
            )
        # Should include the expected error message in the exception.
        assert "Audio file not found: /invalid/audio.mp3" in str(exc_info.value)
        # Should also log the error message.
        assert "Audio file not found: /invalid/audio.mp3" in caplog.text


@pytest.mark.asyncio
async def test_validate_paths_destination_not_found(
    transcription_service: TranscriptionService, caplog: pytest.LogCaptureFixture
) -> None:
    """Should raise FileNotFoundError when the destination directory is not found."""
    with patch(
        "core.brevio.services.transcription_service.exists",
        side_effect=[True, False],
    ):
        with pytest.raises(FileNotFoundError) as exc_info:
            transcription_service._validate_paths(
                "/valid/audio.mp3", "./backend/audios"
            )
        # Should include the expected error message in the exception.
        assert "Destination directory not found: ./backend/audios" in str(
            exc_info.value
        )
        # Should also log the error message.
        assert "Destination directory not found: ./backend/audios" in caplog.text


@pytest.mark.asyncio
async def test_generate_transcription_unexpected_error(
    transcription_service: TranscriptionService, caplog: pytest.LogCaptureFixture
) -> None:
    mock_model = Mock()
    mock_model.transcribe.side_effect = ValueError("Invalid data")
    destination_path = "./backend/audios"

    with patch("whisper.load_model", return_value=mock_model), patch(
        "core.brevio.services.transcription_service.exists", return_value=True
    ), pytest.raises(ValueError) as exc_info:
        await transcription_service.generate_transcription(
            audio_path="/audio.mp3",
            destination_path=destination_path,
            language=LanguageType.SPANISH,
        )
    assert "Unexpected error in transcription: Invalid data" in caplog.text
    assert str(exc_info.value) == "Invalid data"


@pytest.mark.asyncio
async def test_generate_transcription_success(
    transcription_service: TranscriptionService, caplog: pytest.LogCaptureFixture
) -> None:
    """Should successfully generate a transcription with formatted timestamps."""
    # Mock result from whisper
    mock_result: Dict[str, List[Dict[str, Union[float, str]]]] = {
        "segments": [
            {"start": 0.0, "text": "Hola mundo"},
            {"start": 2.5, "text": "Esto es una prueba"},
        ]
    }

    # Setup mocks
    mock_model = Mock()
    mock_model.transcribe.return_value = mock_result
    destination_path = "./backend/audios"

    # Mock format_time function to return specific values
    mock_format_time = Mock(
        side_effect=lambda x: {
            0.0: "[00:00:00]",
            2.5: "[00:00:02]",
        }.get(x, "[00:00:XX]")
    )

    # Mock _write_transcription method directly
    write_transcription_mock = Mock()

    # Reset mocks before test
    with patch("whisper.load_model", return_value=mock_model), patch(
        "core.brevio.services.transcription_service.exists", return_value=True
    ), patch(
        "core.brevio.services.transcription_service.format_time", mock_format_time
    ), patch.object(
        transcription_service, "_write_transcription", write_transcription_mock
    ):
        # Call the method
        result = await transcription_service.generate_transcription(
            audio_path="/audio.mp3",
            destination_path=destination_path,
            language=LanguageType.SPANISH,
        )

        # Expected result
        expected_text = "[00:00:00] Hola mundo\n[00:00:02] Esto es una prueba"

        # Verify results
        assert result == expected_text
        assert "Starting transcription for /audio.mp3 in es" in caplog.text

        # Verify _write_transcription was called once with correct parameters
        write_transcription_mock.assert_called_once()
        # Check the first argument of the first call
        args, _ = write_transcription_mock.call_args
        assert args[1] == expected_text

        # Verify format_time was called correctly
        assert mock_format_time.call_count == 2
        mock_format_time.assert_any_call(0.0)
        mock_format_time.assert_any_call(2.5)


@pytest.mark.asyncio
async def test_generate_transcription_custom_format_time(
    transcription_service: TranscriptionService,
) -> None:
    """Should use the format_time function to format timestamps correctly."""
    # Mock transcription result
    mock_result: Dict[str, List[Dict[str, Union[float, str]]]] = {
        "segments": [{"start": 1.5, "text": "Custom"}]
    }

    # Setup mocks
    mock_model = Mock()
    mock_model.transcribe.return_value = mock_result
    destination_path = "./backend/audios"
    transcription_path = f"{destination_path}/{Constants.TRANSCRIPTION_FILE}"

    # Mock format_time function
    mock_format_time = Mock(return_value="[00:00:01]")

    # Mock _write_transcription method
    write_transcription_mock = Mock()

    # Patch dependencies
    with patch("whisper.load_model", return_value=mock_model), patch(
        "core.brevio.services.transcription_service.exists", return_value=True
    ), patch(
        "core.brevio.services.transcription_service.format_time", mock_format_time
    ), patch.object(
        transcription_service, "_write_transcription", write_transcription_mock
    ):
        # Call the method
        result = await transcription_service.generate_transcription(
            audio_path="/audio.mp3",
            destination_path=destination_path,
            language=LanguageType.ENGLISH,
        )

        # Expected result
        expected_text = "[00:00:01] Custom"

        # Verify results
        assert result == expected_text
        mock_format_time.assert_called_once_with(1.5)
        write_transcription_mock.assert_called_once()
        args, _ = write_transcription_mock.call_args
        assert args[1] == expected_text


@pytest.mark.asyncio
async def test_generate_transcription_no_segments(
    transcription_service: TranscriptionService, caplog: pytest.LogCaptureFixture
) -> None:
    """Should handle the case where no segments are returned."""
    # Mock result with empty segments
    mock_result: Dict[str, List[Dict[str, Union[float, str]]]] = {"segments": []}

    # Create mock model
    mock_model = Mock()
    mock_model.transcribe.return_value = mock_result

    # Setup path mocks
    destination_path = "./test_output"
    transcription_path = f"{destination_path}/{Constants.TRANSCRIPTION_FILE}"

    # Patch dependencies en el módulo donde se usan las funciones importadas directamente
    with patch("whisper.load_model", return_value=mock_model), patch(
        "core.brevio.services.transcription_service.exists", return_value=True
    ), patch(
        "core.brevio.services.transcription_service.join",
        return_value=transcription_path,
    ), patch(
        "pathlib.Path.exists", return_value=True
    ), patch(
        "builtins.open", new_callable=MagicMock
    ) as mock_open, patch.object(
        transcription_service._directory_manager, "read_transcription", return_value=""
    ):
        # Call the method
        result = await transcription_service.generate_transcription(
            audio_path="./test_audio.mp3",  # Use relative path
            destination_path=destination_path,
            language=LanguageType.ENGLISH,
        )

        # Verify results
        assert result == ""
        assert "Starting transcription for ./test_audio.mp3 in en" in caplog.text
        assert "No segments found in transcription result" in caplog.text

        # Verify file operations - ensure open is called once and write() method is called with an empty string
        mock_open.assert_called_once_with(transcription_path, "w", encoding="utf-8")
        mock_open.return_value.__enter__.return_value.write.assert_called_once_with("")


@pytest.mark.asyncio
async def test_generate_transcription_runtime_error(
    transcription_service: TranscriptionService, caplog: pytest.LogCaptureFixture
) -> None:
    """Should handle RuntimeError from whisper properly."""
    # Setup mock to raise an error
    mock_model = Mock()
    mock_model.transcribe.side_effect = RuntimeError("Whisper failed")
    destination_path = "../../data"

    # Apply patches
    with patch("whisper.load_model", return_value=mock_model), patch(
        "core.brevio.services.transcription_service.exists", return_value=True
    ), pytest.raises(RuntimeError) as exc_info:
        # Call with awaiting
        await transcription_service.generate_transcription(
            audio_path="/audio.mp3",
            destination_path=destination_path,
            language=LanguageType.SPANISH,
        )

    # Check error handling
    assert "Unexpected error in transcription: Whisper failed" in caplog.text
    assert str(exc_info.value) == "Whisper failed"


@pytest.mark.asyncio
async def test_generate_transcription_io_error(
    transcription_service: TranscriptionService, caplog: pytest.LogCaptureFixture
) -> None:
    """Should handle IOError when writing the transcription file."""
    # Mock successful transcription but IOError on file write
    mock_result: Dict[str, List[Dict[str, Union[float, str]]]] = {
        "segments": [{"start": 0.0, "text": "Test"}]
    }
    mock_model = Mock()
    mock_model.transcribe.return_value = mock_result
    destination_path = "../../data"
    transcription_path = f"{destination_path}/{Constants.TRANSCRIPTION_FILE}"

    # Apply patches
    with patch("whisper.load_model", return_value=mock_model), patch(
        "core.brevio.services.transcription_service.exists", return_value=True
    ), patch("os.path.join", return_value=transcription_path), patch(
        "builtins.open", side_effect=IOError("No space left")
    ), pytest.raises(
        IOError
    ) as exc_info:
        # Call with awaiting
        await transcription_service.generate_transcription(
            audio_path="/audio.mp3",
            destination_path=destination_path,
            language=LanguageType.SPANISH,
        )

    # Check error handling
    assert "Unexpected error in transcription: No space left" in caplog.text
    assert str(exc_info.value) == "No space left"
