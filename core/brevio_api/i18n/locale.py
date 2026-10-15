"""Locale resolution for backend requests via Accept-Language header."""

from __future__ import annotations

from typing import Sequence

SUPPORTED_LOCALES: Sequence[str] = (
    "en",
    "es",
    "pt",
    "fr",
    "de",
    "it",
    "ru",
    "zh",
    "ja",
    "ko",
    "ar",
    "hi",
)

DEFAULT_LOCALE: str = "en"


def parse_accept_language(header: str | None) -> list[str]:
    """Parse Accept-Language header into ordered list of locale codes."""
    if not header or not header.strip():
        return []
    tags = []
    for piece in header.split(","):
        part = piece.split(";")[0].strip().lower()
        if not part:
            continue
        # Extract primary subtag (e.g. "es-ES" -> "es")
        base = part.split("-")[0].strip()
        if base:
            tags.append(base)
    return tags


def resolve_request_locale(accept_language_header: str | None = None) -> str:
    """Resolve Accept-Language header to supported backend locale.

    Never falls back to system locale. Uses DEFAULT_LOCALE if unsupported.
    """
    candidates = parse_accept_language(accept_language_header)
    for candidate in candidates:
        if candidate in SUPPORTED_LOCALES:
            return candidate
    return DEFAULT_LOCALE
