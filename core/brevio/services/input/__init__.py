from __future__ import annotations

from typing import Any

from core.brevio.services.input.provider import MediaInputProvider
from core.brevio.services.input.uploaded_media import UploadedMediaInputProvider
from core.brevio.services.input.youtube import YouTubeInputProvider
from core.brevio.services.yt_service import YTService


def media_input_provider_for(
    video: Any, *, yt_service: YTService
) -> MediaInputProvider:
    url = getattr(video, "url", None)
    path = getattr(video, "path", None)
    if url:
        return YouTubeInputProvider(str(url), yt_service)
    if path:
        return UploadedMediaInputProvider(str(path))
    raise ValueError("Se requiere 'url' o 'path'")
