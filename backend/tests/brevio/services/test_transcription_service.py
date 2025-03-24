import pytest
import logging
from unittest.mock import patch, Mock, MagicMock
from backend.brevio.services.transcription_service import TranscriptionService
from backend.brevio.enums.language import LanguageType
from backend.brevio.constants.constants import Constants

@pytest.fixture
def caplog(caplog):
    """Should set the logging level to DEBUG for transcription service tests."""
    caplog.set_level(logging.DEBUG)
    return caplog

@pytest.fixture
def transcription_service():
    """Should provide a fresh instance of TranscriptionService for testing by resetting the singleton."""
    TranscriptionService._instance = None
    return TranscriptionService()

@pytest.mark.asyncio
async def test_singleton_instance(caplog):
    """Should verify that TranscriptionService is implemented as a singleton."""
    caplog.set_level(logging.DEBUG, logger="backend.brevio.services.transcription_service")
    first_instance = TranscriptionService()
    second_instance = TranscriptionService()
    # Should return the same instance for both calls.
    assert first_instance is second_instance
    # Should log messages indicating instance creation and reuse.
    assert "Creating new instance of TranscriptionService" in caplog.text
    assert "Reusing existing instance of TranscriptionService" in caplog.text

@pytest.mark.asyncio
async def test_init_directory_manager(transcription_service):
    """Should initialize DirectoryManager only once."""
    # Should have a _directory_manager attribute that is not None.
    assert hasattr(transcription_service, '_directory_manager')
    assert transcription_service._directory_manager is not None
    old_manager = transcription_service._directory_manager
    # Should not reinitialize _directory_manager on subsequent __init__ calls.
    transcription_service.__init__()
    assert transcription_service._directory_manager is old_manager

@pytest.mark.asyncio
async def test_validate_paths_success(transcription_service):
    """Should not raise any errors when valid paths are provided."""
    with patch('backend.brevio.services.transcription_service.exists', return_value=True):
        # Should validate the provided audio and destination paths successfully.
        transcription_service._validate_paths("./backend/audios/audio.mp3", "./backend/audios")

@pytest.mark.asyncio
async def test_validate_paths_audio_not_found(transcription_service, caplog):
    """Should raise FileNotFoundError when the audio file is not found."""
    with patch('backend.brevio.services.transcription_service.exists', side_effect=[False, True]):
        with pytest.raises(FileNotFoundError) as exc_info:
            transcription_service._validate_paths("/invalid/audio.mp3", "./backend/audios")
        # Should include the expected error message in the exception.
        assert "Audio file not found: /invalid/audio.mp3" in str(exc_info.value)
        # Should also log the error message.
        assert "Audio file not found: /invalid/audio.mp3" in caplog.text

@pytest.mark.asyncio
async def test_validate_paths_destination_not_found(transcription_service, caplog):
    """Should raise FileNotFoundError when the destination directory is not found."""
    with patch('backend.brevio.services.transcription_service.exists', side_effect=[True, False]):
        with pytest.raises(FileNotFoundError) as exc_info:
            transcription_service._validate_paths("/valid/audio.mp3", "./backend/audios")
        # Should include the expected error message in the exception.
        assert "Destination directory not found: ./backend/audios" in str(exc_info.value)
        # Should also log the error message.
        assert "Destination directory not found: ./backend/audios" in caplog.text

@pytest.mark.asyncio
async def test_generate_transcription_success(transcription_service, caplog):
    """Should successfully generate a transcription with valid segments."""
    mock_result = {
        "segments": [
            {"start": 0.0, "text": "Hola mundo"},
            {"start": 2.5, "text": "Esto es una prueba"}
        ]
    }
    mock_model = Mock()
    mock_model.transcribe.return_value = mock_result
    destination_path = "./backend/audios"
    transcription_path = f"{destination_path}/{Constants.TRANSCRIPTION_FILE}"

    with patch('whisper.load_model', return_value=mock_model), \
         patch('backend.brevio.services.transcription_service.exists', return_value=True), \
         patch('os.path.join', return_value=transcription_path), \
         patch('builtins.open', new_callable=MagicMock) as mock_open, \
         patch.object(transcription_service._directory_manager, 'read_transcription', return_value="transcripción leída"):
        
        result = transcription_service.generate_transcription(
            audio_path="/audio.mp3",
            destination_path=destination_path,
            language=LanguageType.SPANISH
        )

        # Should return the transcription read from the directory manager.
        assert result == "transcripción leída"
        # Should log the start of the transcription process with the correct language code.
        assert "Starting transcription for /audio.mp3 in es" in caplog.text
        # Should log the successful transcription completion message.
        assert "Transcription completed successfully" in caplog.text
        # Should log the file path where the transcription was written.
        assert f"Transcription written to {transcription_path}" in caplog.text
        # Should call the transcribe method with the correct audio path and language.
        mock_model.transcribe.assert_called_once_with("/audio.mp3", language="es")
        # Should write the correctly formatted transcription text to the file.
        mock_open.return_value.__enter__.return_value.write.assert_called_once_with(
            "[00:00:00] Hola mundo\n[00:00:02] Esto es una prueba"
        )

@pytest.mark.asyncio
async def test_generate_transcription_no_segments(transcription_service, caplog):
    """Should handle transcription when no segments are returned by returning an empty string."""
    mock_result = {"segments": []}
    mock_model = Mock()
    mock_model.transcribe.return_value = mock_result
    destination_path = "./backend/audios"
    transcription_path = f"{destination_path}/{Constants.TRANSCRIPTION_FILE}"

    with patch('whisper.load_model', return_value=mock_model), \
         patch('backend.brevio.services.transcription_service.exists', return_value=True), \
         patch('os.path.join', return_value=transcription_path), \
         patch('builtins.open', new_callable=MagicMock) as mock_open, \
         patch.object(transcription_service._directory_manager, 'read_transcription', return_value=""):
        
        result = transcription_service.generate_transcription(
            audio_path="/audio.mp3",
            destination_path=destination_path,
            language=LanguageType.ENGLISH
        )

        # Should return an empty string when no transcription segments are available.
        assert result == ""
        # Should log the start of the transcription process with the correct language code.
        assert "Starting transcription for /audio.mp3 in en" in caplog.text
        # Should write an empty string to the transcription file.
        mock_open.return_value.__enter__.return_value.write.assert_called_once_with("")

@pytest.mark.asyncio
async def test_generate_transcription_runtime_error(transcription_service, caplog):
    """Should raise a RuntimeError when the Whisper model fails during transcription."""
    mock_model = Mock()
    mock_model.transcribe.side_effect = RuntimeError("Whisper failed")
    destination_path = "./backend/audios"

    with patch('whisper.load_model', return_value=mock_model), \
         patch('backend.brevio.services.transcription_service.exists', return_value=True), \
         pytest.raises(RuntimeError) as exc_info:
        
        transcription_service.generate_transcription(
            audio_path="/audio.mp3",
            destination_path=destination_path,
            language=LanguageType.SPANISH
        )

    # Should log the error message indicating Whisper transcription failure.
    assert "Whisper transcription failed: Whisper failed" in caplog.text
    # Should raise the RuntimeError with the correct error message.
    assert str(exc_info.value) == "Whisper failed"

@pytest.mark.asyncio
async def test_generate_transcription_io_error(transcription_service, caplog):
    """Should raise an IOError when an IO error occurs while writing the transcription file."""
    mock_result = {"segments": [{"start": 0.0, "text": "Test"}]}
    mock_model = Mock()
    mock_model.transcribe.return_value = mock_result
    destination_path = "./backend/audios"
    transcription_path = f"{destination_path}/{Constants.TRANSCRIPTION_FILE}"

    with patch('whisper.load_model', return_value=mock_model), \
         patch('backend.brevio.services.transcription_service.exists', return_value=True), \
         patch('os.path.join', return_value=transcription_path), \
         patch('builtins.open', side_effect=IOError("No space left")), \
         pytest.raises(IOError) as exc_info:
        
        transcription_service.generate_transcription(
            audio_path="/audio.mp3",
            destination_path=destination_path,
            language=LanguageType.SPANISH
        )

    # Should log the IO error message.
    assert "IO error during transcription: No space left" in caplog.text
    # Should raise the IOError with the correct error message.
    assert str(exc_info.value) == "No space left"

@pytest.mark.asyncio
async def test_generate_transcription_unexpected_error(transcription_service, caplog):
    """Should raise an unexpected error when an unknown error occurs during transcription."""
    mock_model = Mock()
    mock_model.transcribe.side_effect = ValueError("Invalid data")
    destination_path = "./backend/audios"

    with patch('whisper.load_model', return_value=mock_model), \
         patch('backend.brevio.services.transcription_service.exists', return_value=True), \
         pytest.raises(ValueError) as exc_info:
        
        transcription_service.generate_transcription(
            audio_path="/audio.mp3",
            destination_path=destination_path,
            language=LanguageType.SPANISH
        )

    # Should log the unexpected error message.
    assert "Unexpected error in transcription: Invalid data" in caplog.text
    # Should raise the ValueError with the correct error message.
    assert str(exc_info.value) == "Invalid data"

@pytest.mark.asyncio
async def test_generate_transcription_custom_format_time(transcription_service, caplog):
    """Should use a custom time format when generating the transcription output."""
    mock_result = {"segments": [{"start": 1.5, "text": "Custom"}]}
    mock_model = Mock()
    mock_model.transcribe.return_value = mock_result
    destination_path = "./backend/audios"
    transcription_path = f"{destination_path}/{Constants.TRANSCRIPTION_FILE}"

    with patch('whisper.load_model', return_value=mock_model), \
         patch('backend.brevio.services.transcription_service.exists', return_value=True), \
         patch('os.path.join', return_value=transcription_path), \
         patch('builtins.open', new_callable=MagicMock) as mock_open, \
         patch.object(transcription_service._directory_manager, 'read_transcription', return_value="custom text"), \
         patch.object(transcription_service, '_format_time', return_value="00:01:50") as mock_format_time:
        
        result = transcription_service.generate_transcription(
            audio_path="/audio.mp3",
            destination_path=destination_path,
            language=LanguageType.SPANISH
        )

        # Should return the transcription read from the directory manager.
        assert result == "custom text"
        # Should call the _format_time method with the correct segment start time.
        mock_format_time.assert_called_once_with(1.5)
        # Should write the custom formatted transcription to the file.
        mock_open.return_value.__enter__.return_value.write.assert_called_once_with("00:01:50 Custom")
