"""Base definition for target-language linguistic resources.

Provides the schema for chatbot detection, menu headers, structural intros/conclusions,
TOC markers, and document export headings per language.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class LinguisticResource:
    language_code: str
    pdf_default_title: str
    help_phrases: Sequence[str]
    menu_headings: Sequence[str]
    greeting_prefixes: Sequence[str]
    continuation_phrases: Sequence[str]
    intro_heading_regex: str
    conclusion_heading_regex: str
    final_points_replacement: str
    toc_markers: Sequence[str]
    caption_markers: Sequence[str]
    truncated_markers: Sequence[str]
