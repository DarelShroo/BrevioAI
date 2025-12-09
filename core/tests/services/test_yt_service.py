from unittest.mock import MagicMock, patch

import pytest
from pydantic import HttpUrl

from core.brevio.services.yt_service import YTService


@pytest.mark.asyncio
class TestYTService:
    async def test_get_video_info_single_video(self) -> None:
        service = YTService()
        mock_info = {
            "title": "Test Video",
            "webpage_url": "https://www.youtube.com/watch?v=123",
            "duration": 120,
            "thumbnail": "http://example.com/thumb.jpg",
            "id": "123",
        }

        with patch("yt_dlp.YoutubeDL") as mock_dl:
            mock_instance = mock_dl.return_value
            mock_instance.__enter__.return_value = mock_instance
            mock_instance.extract_info.return_value = mock_info

            url = HttpUrl("https://www.youtube.com/watch?v=123")
            result = await service.get_video_info(url)

            assert len(result) == 1
            assert result[0]["title"] == "Test Video"
            assert result[0]["url"] == "https://www.youtube.com/watch?v=123"
            assert result[0]["duration"] == 120

    async def test_get_video_info_playlist(self) -> None:
        service = YTService()
        mock_info = {
            "entries": [
                {
                    "title": "Video 1",
                    "url": "https://www.youtube.com/watch?v=1",
                    "duration": 60,
                    "thumbnail": "thumb1",
                    "id": "1",
                },
                {
                    "title": "Video 2",
                    "url": "https://www.youtube.com/watch?v=2",
                    "duration": 120,
                    "thumbnail": "thumb2",
                    "id": "2",
                },
            ]
        }

        with patch("yt_dlp.YoutubeDL") as mock_dl:
            mock_instance = mock_dl.return_value
            mock_instance.__enter__.return_value = mock_instance
            mock_instance.extract_info.return_value = mock_info

            url = HttpUrl("https://www.youtube.com/playlist?list=123")
            result = await service.get_video_info(url)

            assert len(result) == 2
            assert result[0]["title"] == "Video 1"
            assert result[1]["title"] == "Video 2"
