from __future__ import annotations

from core.brevio.enums.language import LanguageType
from core.brevio.utils.utils import format_time

from .provider import TranscriptionResult, TranscriptionSegment

_LANGUAGE_ALIASES = {
    "por": "pt",
    "zh-cn": "zh",
    "zh-tw": "zh",
    "pt": "pt",
}


def whisper_language_code(language: LanguageType) -> str | None:
    value = language.value.lower()
    if value in _LANGUAGE_ALIASES:
        return _LANGUAGE_ALIASES[value]
    if len(value) == 2 and value.isalpha():
        return value
    if "-" in value:
        prefix = value.split("-", 1)[0]
        if len(prefix) == 2 and prefix.isalpha():
            return prefix
    return None


def format_transcription(result: TranscriptionResult) -> str:
    if result.segments:
        lines = [
            f"{format_time(segment.start)} {segment.text.strip()}".rstrip()
            for segment in result.segments
            if segment.text and segment.text.strip()
        ]
        if lines:
            return "\n".join(lines)
    return (result.text or "").strip()


def segments_from_payload(payload: dict) -> list[TranscriptionSegment]:
    raw_segments = payload.get("segments") or []
    segments: list[TranscriptionSegment] = []
    for item in raw_segments:
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        try:
            start = float(item.get("start") or 0.0)
        except (TypeError, ValueError):
            start = 0.0
        segments.append(TranscriptionSegment(start=start, text=text))
    return segments
