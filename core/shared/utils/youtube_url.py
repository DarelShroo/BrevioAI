"""Strict YouTube URL validation to reduce SSRF via yt-dlp."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from pydantic import HttpUrl

ALLOWED_YOUTUBE_HOSTS = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
        "www.youtu.be",
    }
)

# Constrain paths so arbitrary youtube.com paths are not handed to yt-dlp.
_WATCH_PATH = re.compile(r"^/watch/?$", re.IGNORECASE)
_SHORTS_PATH = re.compile(r"^/shorts/[A-Za-z0-9_-]{6,64}/?$", re.IGNORECASE)
_EMBED_PATH = re.compile(r"^/embed/[A-Za-z0-9_-]{6,64}/?$", re.IGNORECASE)
_PLAYLIST_PATH = re.compile(r"^/playlist/?$", re.IGNORECASE)
_LIVE_PATH = re.compile(r"^/live/[A-Za-z0-9_-]{6,64}/?$", re.IGNORECASE)
_YOUTU_BE_PATH = re.compile(r"^/[A-Za-z0-9_-]{6,64}/?$", re.IGNORECASE)


def _path_allowed(host: str, path: str) -> bool:
    if host in {"youtu.be", "www.youtu.be"}:
        return bool(_YOUTU_BE_PATH.match(path or "/"))
    return bool(
        _WATCH_PATH.match(path)
        or _SHORTS_PATH.match(path)
        or _EMBED_PATH.match(path)
        or _PLAYLIST_PATH.match(path)
        or _LIVE_PATH.match(path)
    )


def normalize_youtube_url(url: str | HttpUrl) -> str:
    raw = str(url).strip()
    parsed = urlparse(raw)
    if parsed.scheme.lower() != "https":
        raise ValueError("YouTube URL must use HTTPS")
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in ALLOWED_YOUTUBE_HOSTS:
        raise ValueError("URL host is not an allowed YouTube domain")
    if parsed.username or parsed.password:
        raise ValueError("YouTube URL must not include credentials")
    if parsed.path in ("", "/"):
        raise ValueError("YouTube URL path is required")
    if not _path_allowed(host, parsed.path):
        raise ValueError("YouTube URL path is not allowed")
    # Reject weird nested userinfo / open-redirect style hosts already covered
    # by hostname parsing; keep a normalized https URL for yt-dlp.
    query = f"?{parsed.query}" if parsed.query else ""
    return f"https://{host}{parsed.path}{query}"
