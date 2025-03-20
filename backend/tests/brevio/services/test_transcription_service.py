import pytest
import logging
from unittest.mock import patch, Mock, MagicMock
from backend.brevio.services.transcription_service import TranscriptionService
from backend.brevio.enums.language import LanguageType
from backend.brevio.constants.constants import Constants

@pytest.fixture
def caplog(caplog):
    caplog.set_level(logging.DEBUG)
    return caplog

@pytest.fixture
def transcription_service():
    TranscriptionService._instance = None
    return TranscriptionService()

@pytest.mark.asyncio
async def test_singleton_instance(caplog):
    """Prueba que TranscriptionService sea un singleton."""
    caplog.set_level(logging.DEBUG, logger="backend.brevio.services.transcription_service")
    first_instance = TranscriptionService()
    second_instance = TranscriptionService()
    assert first_instance is second_instance
    assert "Creating new instance of TranscriptionService" in caplog.text
    assert "Reusing existing instance of TranscriptionService" in caplog.text

@pytest.mark.asyncio
async def test_init_directory_manager(transcription_service):
    """Prueba que DirectoryManager se inicializa solo una vez."""
    assert hasattr(transcription_service, '_directory_manager')
    assert transcription_service._directory_manager is not None
    old_manager = transcription_service._directory_manager
    transcription_service.__init__()
    assert transcription_service._directory_manager is old_manager

@pytest.mark.asyncio
async def test_validate_paths_success(transcription_service):
    """Prueba que _validate_paths no lanza errores con paths válidos."""
    with patch('backend.brevio.services.transcription_service.exists', return_value=True):
        transcription_service._validate_paths("./backend/audios/audio.mp3", "./backend/audios")

@pytest.mark.asyncio
async def test_validate_paths_audio_not_found(transcription_service, caplog):
    """Prueba que _validate_paths lanza FileNotFoundError si el audio no existe."""
    with patch('backend.brevio.services.transcription_service.exists', side_effect=[False, True]):
        with pytest.raises(FileNotFoundError) as exc_info:
            transcription_service._validate_paths("/invalid/audio.mp3", "./backend/audios")
        assert "Audio file not found: /invalid/audio.mp3" in str(exc_info.value)
        assert "Audio file not found: /invalid/audio.mp3" in caplog.text

@pytest.mark.asyncio
async def test_validate_paths_destination_not_found(transcription_service, caplog):
    """Prueba que _validate_paths lanza FileNotFoundError si el destino no existe."""
    with patch('backend.brevio.services.transcription_service.exists', side_effect=[True, False]):
        with pytest.raises(FileNotFoundError) as exc_info:
            transcription_service._validate_paths("/valid/audio.mp3", "./backend/audios")
        assert "Destination directory not found: ./backend/audios" in str(exc_info.value)
        assert "Destination directory not found: ./backend/audios" in caplog.text

@pytest.mark.asyncio
async def test_generate_transcription_success(transcription_service, caplog):
    """Prueba un caso exitoso de transcripción."""
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

        assert result == "transcripción leída"
        assert "Starting transcription for /audio.mp3 in es" in caplog.text
        assert "Transcription completed successfully" in caplog.text
        assert f"Transcription written to {transcription_path}" in caplog.text
        mock_model.transcribe.assert_called_once_with("/audio.mp3", language="es")
        mock_open.return_value.__enter__.return_value.write.assert_called_once_with(
            "[00:00:00] Hola mundo\n[00:00:02] Esto es una prueba"
        )

@pytest.mark.asyncio
async def test_generate_transcription_no_segments(transcription_service, caplog):
    """Prueba transcripción cuando no hay segmentos."""
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

        assert result == ""
        assert "Starting transcription for /audio.mp3 in en" in caplog.text
        mock_open.return_value.__enter__.return_value.write.assert_called_once_with("")

@pytest.mark.asyncio
async def test_generate_transcription_runtime_error(transcription_service, caplog):
    """Prueba error de Whisper durante la transcripción."""
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

    assert "Whisper transcription failed: Whisper failed" in caplog.text
    assert str(exc_info.value) == "Whisper failed"

@pytest.mark.asyncio
async def test_generate_transcription_io_error(transcription_service, caplog):
    """Prueba error de IO al escribir el archivo."""
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

    assert "IO error during transcription: No space left" in caplog.text
    assert str(exc_info.value) == "No space left"

@pytest.mark.asyncio
async def test_generate_transcription_unexpected_error(transcription_service, caplog):
    """Prueba un error inesperado."""
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

    assert "Unexpected error in transcription: Invalid data" in caplog.text
    assert str(exc_info.value) == "Invalid data"

@pytest.mark.asyncio
async def test_generate_transcription_custom_format_time(transcription_service, caplog):
    """Prueba que format_time personalizado funciona."""
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

        assert result == "custom text"
        mock_format_time.assert_called_once_with(1.5)
        mock_open.return_value.__enter__.return_value.write.assert_called_once_with("00:01:50 Custom")