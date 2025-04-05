import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from backend.brevio.services.yt_service import YTService


@pytest.fixture
def yt_service():
    return YTService()


@pytest.mark.asyncio
async def test_download_success(yt_service):
    """Should successfully download a video and return a success message."""
    with patch("yt_dlp.YoutubeDL") as mock_yt:
        mock_instance = mock_yt.return_value.__enter__.return_value
        mock_instance.download.return_value = None
        result = await yt_service.download(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "./backend/audios"
        )
        assert result == "Descarga exitosa"
        mock_instance.download.assert_called_once_with(
            ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
        )


@pytest.mark.asyncio
async def test_download_failure(yt_service):
    """Should return an error message when the download fails."""
    with patch("yt_dlp.YoutubeDL") as mock_yt:
        mock_instance = mock_yt.return_value.__enter__.return_value
        mock_instance.download.side_effect = Exception("Error al descargar")
        result = await yt_service.download(
            "https://www.youtube.com/watch?v=azucx", "./backend/audios"
        )
        assert "Error en descarga: Error al descargar" in result


@pytest.mark.asyncio
async def test_process_video(yt_service):
    """Should process a single video by calling download with the correct parameters."""
    with patch.object(yt_service, "download", new_callable=AsyncMock) as mock_download:
        mock_download.return_value = "Descarga exitosa"
        await yt_service.process_video(
            1, "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "./backend/audios"
        )
        mock_download.assert_called_once_with(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "./backend/audios", None
        )


@pytest.mark.asyncio
async def test_process_videos(yt_service):
    """Should process multiple videos concurrently and call download for each one."""
    with patch.object(yt_service, "download", new_callable=AsyncMock) as mock_download:
        mock_download.return_value = "Descarga exitosa"
        videos = [
            {
                "id": 1,
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "dest_folder": "./backend/audios",
            },
            {
                "id": 2,
                "url": "https://www.youtube.com/watch?v=3JZ_D3ELwOQ",
                "dest_folder": "./backend/audios",
            },
        ]
        await yt_service.process_videos(videos)
        assert mock_download.call_count == 2


@pytest.mark.asyncio
async def test_get_video_urls_from_playlist(yt_service):
    """Should extract and return a list of video URLs from a YouTube playlist."""
    mock_info = {
        "entries": [
            {"url": "https://www.youtube.com/watch?v=abc"},
            {"url": "https://www.youtube.com/watch?v=def"},
        ]
    }
    with patch("yt_dlp.YoutubeDL") as mock_yt:
        mock_instance = mock_yt.return_value.__enter__.return_value
        mock_instance.extract_info.return_value = mock_info
        urls = await yt_service.get_video_urls_from_playlist(
            "https://www.youtube.com/playlist?list=PL123"
        )
        expected_urls = [
            "https://www.youtube.com/watch?v=abc",
            "https://www.youtube.com/watch?v=def",
        ]
        assert urls == expected_urls
        mock_instance.extract_info.assert_called_once_with(
            "https://www.youtube.com/playlist?list=PL123", download=False
        )


@pytest.mark.asyncio
async def test_get_media_duration_playlist(yt_service):
    """Should return the durations of all videos in a playlist."""
    mock_durations = [
        {"url": "https://www.youtube.com/watch?v=abc", "duration": 300},
        {"url": "https://www.youtube.com/watch?v=def", "duration": 450},
    ]
    with patch.object(
        yt_service,
        "get_video_urls_from_playlist",
        return_value=[
            "https://www.youtube.com/watch?v=abc",
            "https://www.youtube.com/watch?v=def",
        ],
    ), patch.object(yt_service, "get_video_duration", side_effect=[300, 450]):
        result = await yt_service.get_media_duration(
            "https://www.youtube.com/playlist?list=PL123"
        )
        assert result == {"durations": mock_durations}


@pytest.mark.asyncio
async def test_count_media_in_yt_playlist(yt_service):
    """Should count the number of media items in a YouTube playlist."""
    mock_info = {
        "entries": [
            {"url": "https://www.youtube.com/watch?v=abc"},
            {"url": "https://www.youtube.com/watch?v=def"},
            {"url": "https://www.youtube.com/watch?v=ghi"},
            {"url": "https://www.youtube.com/watch?v=jkl"},
            {"url": "https://www.youtube.com/watch?v=mno"},
        ]
    }
    with patch("yt_dlp.YoutubeDL") as mock_yt:
        mock_instance = mock_yt.return_value.__enter__.return_value
        mock_instance.extract_info.return_value = mock_info
        count = await yt_service.count_media_in_yt_playlist(
            "https://www.youtube.com/playlist?list=PL123"
        )
        assert count == 5
        mock_instance.extract_info.assert_called_once_with(
            "https://www.youtube.com/playlist?list=PL123", download=False
        )


@pytest.mark.asyncio
async def test_get_video_duration(yt_service):
    """Should return the duration of a single YouTube video."""
    mock_info = {"duration": 300}
    with patch("yt_dlp.YoutubeDL") as mock_yt:
        mock_instance = mock_yt.return_value.__enter__.return_value
        mock_instance.extract_info.return_value = mock_info
        duration = await yt_service.get_video_duration(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        assert duration == 300
        mock_instance.extract_info.assert_called_once_with(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ", download=False
        )


@pytest.mark.asyncio
async def test_get_media_duration_video(yt_service):
    """Should return the duration of a single video when not a playlist."""
    mock_info = {"duration": 300}
    with patch("yt_dlp.YoutubeDL") as mock_yt:
        mock_instance = mock_yt.return_value.__enter__.return_value
        mock_instance.extract_info.return_value = mock_info
        result = await yt_service.get_media_duration(
            "https://www.youtube.com/watch?v=abc"
        )
        assert result == {
            "durations": [
                {"url": "https://www.youtube.com/watch?v=abc", "duration": 300}
            ]
        }


@pytest.mark.asyncio
async def test_is_youtube_playlist_true(yt_service):
    """Should return True when the URL is a YouTube playlist."""
    url = "https://www.youtube.com/playlist?list=PL123"
    result = await yt_service.is_youtube_playlist(url)
    assert result is True


@pytest.mark.asyncio
async def test_is_youtube_playlist_false(yt_service):
    """Should return False when the URL is not a YouTube playlist."""
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    result = await yt_service.is_youtube_playlist(url)
    assert result is False
