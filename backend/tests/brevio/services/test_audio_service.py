import pytest
import logging
from unittest.mock import patch, Mock
from backend.brevio.services.audio_service import AudioService 
from pydantic import HttpUrl
import multiprocessing

multiprocessing.set_start_method("spawn", force=True)

@pytest.fixture
def caplog(caplog):
    caplog.set_level(logging.DEBUG, logger="backend.brevio.services.audio_service")
    return caplog

@pytest.fixture
def audio_service():
    return AudioService()

@pytest.mark.asyncio
async def test_get_media_info_success(audio_service, caplog):
    """Prueba que get_media_info extrae correctamente título y duración."""
    mock_result = Mock()
    mock_result.stdout = ""
    mock_result.stderr = "Duration: 01:02:03.45, other info"

    with patch('backend.brevio.services.audio_service.subprocess.run', return_value=mock_result):
        result = await audio_service.get_media_info("/path/to/test.mp3")
        
        assert result == {"title": "test", "duration": pytest.approx(62.0575)}  # 1h 2m 3.45s = 62.0575 min
        assert "Processing media file: /path/to/test.mp3" in caplog.text
        assert "Extracted title: test" in caplog.text
        assert "Calculated duration: 62.0575 minutes" in caplog.text

@pytest.mark.asyncio
async def test_get_media_info_no_duration(audio_service, caplog):
    """Prueba que get_media_info devuelve None si no hay duración."""
    mock_result = Mock()
    mock_result.stdout = ""
    mock_result.stderr = "No duration here"

    with patch('backend.brevio.services.audio_service.subprocess.run', return_value=mock_result):
        result = await audio_service.get_media_info("/path/to/test.mp3")
        
        assert result is None
        assert "Processing media file: /path/to/test.mp3" in caplog.text
        assert "Extracted title: test" in caplog.text
        assert "No duration found in file: /path/to/test.mp3" in caplog.text

@pytest.mark.asyncio
async def test_get_media_info_yt_success(audio_service, caplog):
    """Prueba que get_media_info_yt extrae correctamente título y duración de YouTube."""
    mock_info = {"title": "Test Video", "duration": 3661}  # 1h 1m 1s
    mock_ydl = Mock()
    mock_ydl.__enter__ = Mock(return_value=mock_ydl)
    mock_ydl.__exit__ = Mock(False)
    mock_ydl.extract_info.return_value = mock_info

    with patch('backend.brevio.services.audio_service.yt_dlp.YoutubeDL', return_value=mock_ydl):
        url = HttpUrl("https://youtube.com/watch?v=test")
        result = await audio_service.get_media_info_yt(url)
        
        assert result == {"title": "Test Video", "duration": 3661}
        assert "Fetching YouTube media info from URL: https://youtube.com/watch?v=test" in caplog.text
        assert "Extracted YouTube info: {'title': 'Test Video', 'duration': 3661}" in caplog.text

@pytest.mark.asyncio
async def test_get_media_info_yt_no_info(audio_service, caplog):
    """Prueba que get_media_info_yt devuelve None si no hay info."""
    mock_ydl = Mock()
    mock_ydl.__enter__ = Mock(return_value=mock_ydl)
    mock_ydl.__exit__ = Mock(False)
    mock_ydl.extract_info.return_value = None

    with patch('backend.brevio.services.audio_service.yt_dlp.YoutubeDL', return_value=mock_ydl):
        url = HttpUrl("https://youtube.com/watch?v=invalid")
        result = await audio_service.get_media_info_yt(url)
        
        assert result is None
        assert "Fetching YouTube media info from URL: https://youtube.com/watch?v=invalid" in caplog.text
        assert "No info extracted from YouTube URL: https://youtube.com/watch?v=invalid" in caplog.text


@pytest.mark.asyncio
async def test_get_media_info_exception(audio_service, caplog):
    """Prueba que get_media_info lanza una excepción en caso de error."""
    with patch('backend.brevio.services.audio_service.subprocess.run', side_effect=Exception("FFmpeg crashed")):
        with pytest.raises(Exception) as exc_info:
            await audio_service.get_media_info("/path/to/test.mp3")
    
        # Corregir la comparación del mensaje
        assert "Ha ocurrido un error inesperado al obtener información del video" in str(exc_info.value)
        assert "/path/to/test.mp3" in str(exc_info.value)

@pytest.mark.asyncio
async def test_get_media_info_yt_exception(audio_service, caplog):
    """Prueba que get_media_info_yt lanza una excepción en caso de error."""
    with patch('backend.brevio.services.audio_service.yt_dlp.YoutubeDL', side_effect=Exception("YouTube API error")):
        url = HttpUrl("https://youtube.com/watch?v=test")
        with pytest.raises(Exception) as exc_info:
            await audio_service.get_media_info_yt(url)
        
        assert "Ha ocurrido un error inesperado al obtener información del video https://youtube.com/watch?v=test" in str(exc_info.value)
        assert "Fetching YouTube media info from URL: https://youtube.com/watch?v=test" in caplog.text
        assert "Error fetching YouTube info from https://youtube.com/watch?v=test: YouTube API error" in caplog.text
