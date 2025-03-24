import pytest
import logging
from unittest.mock import patch, Mock
from backend.brevio.services.audio_service import AudioService 
from pydantic import HttpUrl
import multiprocessing

multiprocessing.set_start_method("spawn", force=True)

@pytest.fixture
def caplog(caplog):
    """Fixture that should set the logging level for audio_service tests."""
    caplog.set_level(logging.DEBUG, logger="backend.brevio.services.audio_service")
    return caplog

@pytest.fixture
def audio_service():
    """Fixture that should instantiate the AudioService."""
    return AudioService()

@pytest.mark.asyncio
async def test_get_media_info_success(audio_service, caplog):
    """Should extract title and duration correctly using get_media_info."""
    mock_result = Mock()
    mock_result.stdout = ""
    mock_result.stderr = "Duration: 01:02:03.45, other info"

    with patch('backend.brevio.services.audio_service.subprocess.run', return_value=mock_result):
        result = await audio_service.get_media_info("/path/to/test.mp3")
        
        # Should return a dictionary with the title and calculated duration in minutes.
        assert result == {"title": "test", "duration": pytest.approx(62.0575)}  # 1h 2m 3.45s = 62.0575 minutes
        # Should log the processing steps for the media file.
        assert "Processing media file: /path/to/test.mp3" in caplog.text
        assert "Extracted title: test" in caplog.text
        assert "Calculated duration: 62.0575 minutes" in caplog.text

@pytest.mark.asyncio
async def test_get_media_info_no_duration(audio_service, caplog):
    """Should return None when no duration is found in get_media_info."""
    mock_result = Mock()
    mock_result.stdout = ""
    mock_result.stderr = "No duration here"

    with patch('backend.brevio.services.audio_service.subprocess.run', return_value=mock_result):
        result = await audio_service.get_media_info("/path/to/test.mp3")
        
        # Should return None if duration is not found.
        assert result is None
        # Should log the processing steps and the missing duration.
        assert "Processing media file: /path/to/test.mp3" in caplog.text
        assert "Extracted title: test" in caplog.text
        assert "No duration found in file: /path/to/test.mp3" in caplog.text

@pytest.mark.asyncio
async def test_get_media_info_yt_success(audio_service, caplog):
    """Should extract title and duration correctly from YouTube using get_media_info_yt."""
    mock_info = {"title": "Test Video", "duration": 3661}  # 1h 1m 1s
    mock_ydl = Mock()
    mock_ydl.__enter__ = Mock(return_value=mock_ydl)
    mock_ydl.__exit__ = Mock(False)
    mock_ydl.extract_info.return_value = mock_info

    with patch('backend.brevio.services.audio_service.yt_dlp.YoutubeDL', return_value=mock_ydl):
        url = HttpUrl("https://youtube.com/watch?v=test")
        result = await audio_service.get_media_info_yt(url)
        
        # Should return a dictionary with the YouTube video title and duration.
        assert result == {"title": "Test Video", "duration": 3661}
        # Should log the process of fetching and extracting YouTube info.
        assert "Fetching YouTube media info from URL: https://youtube.com/watch?v=test" in caplog.text
        assert "Extracted YouTube info: {'title': 'Test Video', 'duration': 3661}" in caplog.text

@pytest.mark.asyncio
async def test_get_media_info_yt_no_info(audio_service, caplog):
    """Should return None when no info is extracted from YouTube in get_media_info_yt."""
    mock_ydl = Mock()
    mock_ydl.__enter__ = Mock(return_value=mock_ydl)
    mock_ydl.__exit__ = Mock(False)
    mock_ydl.extract_info.return_value = None

    with patch('backend.brevio.services.audio_service.yt_dlp.YoutubeDL', return_value=mock_ydl):
        url = HttpUrl("https://youtube.com/watch?v=invalid")
        result = await audio_service.get_media_info_yt(url)
        
        # Should return None if no YouTube info is extracted.
        assert result is None
        # Should log the process of fetching and the absence of info.
        assert "Fetching YouTube media info from URL: https://youtube.com/watch?v=invalid" in caplog.text
        assert "No info extracted from YouTube URL: https://youtube.com/watch?v=invalid" in caplog.text

@pytest.mark.asyncio
async def test_get_media_info_exception(audio_service, caplog):
    """Should raise an exception if an error occurs in get_media_info."""
    with patch('backend.brevio.services.audio_service.subprocess.run', side_effect=Exception("FFmpeg crashed")):
        with pytest.raises(Exception) as exc_info:
            await audio_service.get_media_info("/path/to/test.mp3")
    
        # Should include the error message and file path in the exception.
        assert "Ha ocurrido un error inesperado al obtener información del video" in str(exc_info.value)
        assert "/path/to/test.mp3" in str(exc_info.value)

@pytest.mark.asyncio
async def test_get_media_info_yt_exception(audio_service, caplog):
    """Should raise an exception if an error occurs in get_media_info_yt."""
    with patch('backend.brevio.services.audio_service.yt_dlp.YoutubeDL', side_effect=Exception("YouTube API error")):
        url = HttpUrl("https://youtube.com/watch?v=test")
        with pytest.raises(Exception) as exc_info:
            await audio_service.get_media_info_yt(url)
        
        # Should include the error message and URL in the exception.
        assert "Ha ocurrido un error inesperado al obtener información del video https://youtube.com/watch?v=test" in str(exc_info.value)
        # Should log the process and error details.
        assert "Fetching YouTube media info from URL: https://youtube.com/watch?v=test" in caplog.text
        assert "Error fetching YouTube info from https://youtube.com/watch?v=test: YouTube API error" in caplog.text
