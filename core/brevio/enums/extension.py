from enum import Enum
from typing import FrozenSet, Tuple


class ExtensionType(Enum):
    MP3 = "mp3"
    M4A = "m4a"
    WAV = "wav"
    MP4 = "mp4"
    TXT = "txt"
    DOCX = "docx"
    PDF = "pdf"


AUDIO_EXTENSIONS: Tuple[ExtensionType, ...] = (
    ExtensionType.MP3,
    ExtensionType.M4A,
    ExtensionType.WAV,
)
VIDEO_EXTENSIONS: Tuple[ExtensionType, ...] = (ExtensionType.MP4,)
MEDIA_EXTENSIONS: Tuple[ExtensionType, ...] = AUDIO_EXTENSIONS + VIDEO_EXTENSIONS
DOCUMENT_EXTENSIONS: Tuple[ExtensionType, ...] = (
    ExtensionType.DOCX,
    ExtensionType.PDF,
)

_AUDIO_VALUES: FrozenSet[str] = frozenset(item.value for item in AUDIO_EXTENSIONS)
_VIDEO_VALUES: FrozenSet[str] = frozenset(item.value for item in VIDEO_EXTENSIONS)
_MEDIA_VALUES: FrozenSet[str] = frozenset(item.value for item in MEDIA_EXTENSIONS)
_DOCUMENT_VALUES: FrozenSet[str] = frozenset(item.value for item in DOCUMENT_EXTENSIONS)


def media_extension_values() -> list[str]:
    return [item.value for item in MEDIA_EXTENSIONS]


def document_extension_values() -> list[str]:
    return [item.value for item in DOCUMENT_EXTENSIONS]


def is_audio_extension(extension: str) -> bool:
    return extension.lower().lstrip(".") in _AUDIO_VALUES


def is_video_extension(extension: str) -> bool:
    return extension.lower().lstrip(".") in _VIDEO_VALUES


def is_media_extension(extension: str) -> bool:
    return extension.lower().lstrip(".") in _MEDIA_VALUES


def is_document_extension(extension: str) -> bool:
    return extension.lower().lstrip(".") in _DOCUMENT_VALUES
