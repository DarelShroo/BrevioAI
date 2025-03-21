import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
import yt_dlp
from backend.brevio.services.yt_service import YTService
import multiprocessing

if multiprocessing.current_process().name == 'MainProcess':
    multiprocessing.set_start_method('spawn', force=True)

@pytest.fixture
def yt_service():
    return YTService()

@pytest.mark.asyncio
async def test_download_success(yt_service):
    with patch("yt_dlp.YoutubeDL") as mock_yt:
        mock_yt.return_value.__enter__.return_value.download.return_value = None
        result = await yt_service.download("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "./backend/audios")
        assert result == "Descarga exitosa"

@pytest.mark.asyncio
async def test_download_failure():
    with patch("yt_dlp.YoutubeDL") as mock_yt, patch("asyncio.get_running_loop") as mock_loop:
        mock_executor = MagicMock()
        mock_loop.return_value.run_in_executor = mock_executor
        
        mock_executor.side_effect = Exception("Error al descargar")
        
        yt_service = YTService()
        
        result = await yt_service.download("https://www.youtube.com/watch?v=azucx", "./backend/audios")
        
        assert "Error al descargar" in result

@pytest.mark.asyncio
async def test_process_video(yt_service):
    with patch.object(yt_service, "download", new_callable=AsyncMock) as mock_download:
        mock_download.return_value = "Descarga exitosa"
        await yt_service.process_video(1, "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "./backend/audios")
        mock_download.assert_called_once()

@pytest.mark.asyncio
async def test_process_videos(yt_service):
    with patch.object(yt_service, "process_video", new_callable=AsyncMock) as mock_process_video:
        videos = [
            {"id": 1, "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dest_folder": "./backend/audios"},
            {"id": 2, "url": "https://www.youtube.com/watch?v=3JZ_D3ELwOQ", "dest_folder": "./backend/audios"},
        ]
        await yt_service.process_videos(videos)
        assert mock_process_video.call_count == 2

@pytest.mark.asyncio
async def test_get_video_urls_from_playlist(yt_service):
    mock_info = {
        "entries": [
            {"url": "https://www.youtube.com/watch?v=abc"},
            {"url": "https://www.youtube.com/watch?v=def"}
        ]
    }

    with patch.object(yt_dlp.YoutubeDL, "extract_info", return_value=mock_info):
        urls = await yt_service.get_video_urls_from_playlist("https://www.youtube.com/playlist?list=PL123")
        
        expected_urls = ["https://www.youtube.com/watch?v=abc", "https://www.youtube.com/watch?v=def"]
        
        assert urls == expected_urls


@pytest.mark.asyncio
async def test_get_media_duration_playlist(yt_service):
    mock_durations = [
        {"url": "https://www.youtube.com/watch?v=abc", "duration": 300},
        {"url": "https://www.youtube.com/watch?v=def", "duration": 450},
    ]
    
    with patch.object(yt_service, "get_video_urls_from_playlist", return_value=[
        "https://www.youtube.com/watch?v=abc", 
        "https://www.youtube.com/watch?v=def"
    ]), patch.object(yt_service, "get_video_duration", side_effect=[300, 450]):
        result = await yt_service.get_media_duration("https://www.youtube.com/playlist?list=PL123")
        
        assert result == {"durations": mock_durations}

@pytest.mark.asyncio
async def test_count_media_in_yt_playlist(yt_service):
    mock_info = {
        "entries": [
            {"url": "https://www.youtube.com/watch?v=abc"},
            {"url": "https://www.youtube.com/watch?v=def"},
            {"url": "https://www.youtube.com/watch?v=ghi"},
            {"url": "https://www.youtube.com/watch?v=jkl"},
            {"url": "https://www.youtube.com/watch?v=mno"}
        ]
    }

    with patch.object(asyncio, 'get_running_loop') as mock_loop:
        mock_executor = MagicMock()
        mock_loop.return_value.run_in_executor = mock_executor
        
        async def fake_executor(_, func, *args):
            result = func(*args)
            future = asyncio.Future()
            future.set_result(result)
            return future
        
        mock_executor.side_effect = fake_executor

        with patch('backend.brevio.services.yt_service.sync_extract_count', return_value=len(mock_info["entries"])):
            count = await yt_service.count_media_in_yt_playlist("https://www.youtube.com/playlist?list=PL123")
            assert await count == 5

@pytest.mark.asyncio
async def test_get_video_duration(yt_service):
    mock_info = {
        "duration": 300
    }

    with patch.object(asyncio, 'get_running_loop') as mock_loop:
        mock_executor = MagicMock()
        mock_loop.return_value.run_in_executor = mock_executor
        
        async def fake_executor(_, func, *args):
            result = func(*args)
            future = asyncio.Future()
            future.set_result(result)
            return future
        
        mock_executor.side_effect = fake_executor

        with patch.object(yt_dlp.YoutubeDL, "extract_info", return_value=mock_info):
            duration = await yt_service.get_video_duration("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            print(f"Duración simulada: 300, Duración devuelta: {duration}")
            assert await duration == 300

@pytest.mark.asyncio
async def test_get_media_duration_video(yt_service):
    mock_duration = {"url": "https://www.youtube.com/watch?v=abc", "duration": 300}
    
    with patch.object(yt_service, "get_video_duration", return_value=300):
        result = await yt_service.get_media_duration("https://www.youtube.com/watch?v=abc")
        
        assert result == {"durations": [mock_duration]}


@pytest.mark.asyncio
async def test_is_youtube_playlist_true(yt_service):
    url = "https://www.youtube.com/playlist?list=PL123"
    
    result = await yt_service.is_youtube_playlist(url)
    
    assert result is True


@pytest.mark.asyncio
async def test_is_youtube_playlist_false(yt_service):
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    result = await yt_service.is_youtube_playlist(url)
    
    assert result is False

