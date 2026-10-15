"""Linguistic resources package for AI postprocessing, quality gates, and cleaning."""

from core.brevio.constants.linguistic.base import LinguisticResource
from core.brevio.constants.linguistic.registry import (
    LINGUISTIC_RESOURCES,
    UnsupportedLinguisticLanguageError,
    get_all_caption_markers,
    get_all_chatbot_markers,
    get_all_menu_headings,
    get_all_toc_markers,
    get_all_truncated_markers,
    resolve_linguistic_resource,
)

__all__ = [
    "LinguisticResource",
    "LINGUISTIC_RESOURCES",
    "UnsupportedLinguisticLanguageError",
    "resolve_linguistic_resource",
    "get_all_chatbot_markers",
    "get_all_menu_headings",
    "get_all_toc_markers",
    "get_all_caption_markers",
    "get_all_truncated_markers",
]
