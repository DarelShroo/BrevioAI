"""Registry and resolution logic for linguistic resources across all supported languages.

Provides access to language-specific AI cleanup patterns, quality gate heuristics,
and structural markers without hardcoded language branches across the codebase.
"""

from __future__ import annotations

from typing import Dict, Tuple

from core.brevio.constants.linguistic.arabic import ARABIC_LINGUISTIC
from core.brevio.constants.linguistic.base import LinguisticResource
from core.brevio.constants.linguistic.chinese import CHINESE_LINGUISTIC
from core.brevio.constants.linguistic.english import ENGLISH_LINGUISTIC
from core.brevio.constants.linguistic.french import FRENCH_LINGUISTIC
from core.brevio.constants.linguistic.german import GERMAN_LINGUISTIC
from core.brevio.constants.linguistic.hindi import HINDI_LINGUISTIC
from core.brevio.constants.linguistic.italian import ITALIAN_LINGUISTIC
from core.brevio.constants.linguistic.japanese import JAPANESE_LINGUISTIC
from core.brevio.constants.linguistic.korean import KOREAN_LINGUISTIC
from core.brevio.constants.linguistic.portuguese import PORTUGUESE_LINGUISTIC
from core.brevio.constants.linguistic.russian import RUSSIAN_LINGUISTIC
from core.brevio.constants.linguistic.spanish import SPANISH_LINGUISTIC
from core.brevio.enums.language import LanguageType

LINGUISTIC_RESOURCES: Dict[str, LinguisticResource] = {
    LanguageType.ARABIC.name: ARABIC_LINGUISTIC,
    LanguageType.ENGLISH.name: ENGLISH_LINGUISTIC,
    LanguageType.CHINESE.name: CHINESE_LINGUISTIC,
    LanguageType.CHINESE_SIMPLIFIED.name: CHINESE_LINGUISTIC,
    LanguageType.CHINESE_TRADITIONAL.name: CHINESE_LINGUISTIC,
    LanguageType.SPANISH.name: SPANISH_LINGUISTIC,
    LanguageType.FRENCH.name: FRENCH_LINGUISTIC,
    LanguageType.GERMAN.name: GERMAN_LINGUISTIC,
    LanguageType.HINDI.name: HINDI_LINGUISTIC,
    LanguageType.ITALIAN.name: ITALIAN_LINGUISTIC,
    LanguageType.JAPANESE.name: JAPANESE_LINGUISTIC,
    LanguageType.KOREAN.name: KOREAN_LINGUISTIC,
    LanguageType.PORTUGUESE_PORTUGAL.name: PORTUGUESE_LINGUISTIC,
    LanguageType.PORTUGUESE_BRAZIL.name: PORTUGUESE_LINGUISTIC,
    LanguageType.RUSSIAN.name: RUSSIAN_LINGUISTIC,
}


class UnsupportedLinguisticLanguageError(KeyError):
    """Raised when the requested language has no linguistic resource implementation."""


def resolve_linguistic_resource(
    target_language: LanguageType | str,
) -> LinguisticResource:
    """Return the linguistic resource module for the target output language.

    Never falls back silently to another language. Raises UnsupportedLinguisticLanguageError.
    """
    resolved: LanguageType | None = None
    if isinstance(target_language, str):
        key = target_language.strip().upper()
        for lang in LanguageType:
            if lang.name == key or lang.value == target_language.strip().lower():
                resolved = lang
                break
        if resolved is None:
            raise UnsupportedLinguisticLanguageError(
                f"Unsupported linguistic language: {target_language!r}"
            )
    else:
        resolved = target_language

    try:
        return LINGUISTIC_RESOURCES[resolved.name]
    except KeyError as exc:
        raise UnsupportedLinguisticLanguageError(
            f"No linguistic resource registered for language {resolved.name}"
        ) from exc


def get_all_chatbot_markers() -> Tuple[str, ...]:
    """Aggregate all chatbot help phrases and continuation phrases across all languages."""
    seen: set[str] = set()
    result = []
    for res in LINGUISTIC_RESOURCES.values():
        for phrase in res.help_phrases:
            low = phrase.lower().strip()
            if low and low not in seen:
                seen.add(low)
                result.append(low)
        for phrase in res.continuation_phrases:
            low = phrase.lower().strip()
            if low and low not in seen:
                seen.add(low)
                result.append(low)
    return tuple(result)


def get_all_menu_headings() -> Tuple[str, ...]:
    """Aggregate all menu headings across all registered languages."""
    seen: set[str] = set()
    result = []
    for res in LINGUISTIC_RESOURCES.values():
        for heading in res.menu_headings:
            low = heading.lower().strip()
            if low and low not in seen:
                seen.add(low)
                result.append(low)
    return tuple(result)


def get_all_toc_markers() -> Tuple[str, ...]:
    """Aggregate all TOC and index markers across all registered languages."""
    seen: set[str] = set()
    result = []
    for res in LINGUISTIC_RESOURCES.values():
        for marker in res.toc_markers:
            low = marker.lower().strip()
            if low and low not in seen:
                seen.add(low)
                result.append(low)
    return tuple(result)


def get_all_caption_markers() -> Tuple[str, ...]:
    """Aggregate all caption markers across all registered languages."""
    seen: set[str] = set()
    result = []
    for res in LINGUISTIC_RESOURCES.values():
        for marker in res.caption_markers:
            low = marker.lower().strip()
            if low and low not in seen:
                seen.add(low)
                result.append(low)
    return tuple(result)


def get_all_truncated_markers() -> Tuple[str, ...]:
    """Aggregate all truncated markers across all registered languages."""
    seen: set[str] = set()
    result = []
    for res in LINGUISTIC_RESOURCES.values():
        for marker in res.truncated_markers:
            low = marker.lower().strip()
            if low and low not in seen:
                seen.add(low)
                result.append(low)
    return tuple(result)
