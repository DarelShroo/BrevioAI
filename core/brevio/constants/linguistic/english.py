"""English linguistic resources for AI pipeline cleaning, quality gates, and postprocessing."""

from __future__ import annotations

from core.brevio.constants.linguistic.base import LinguisticResource

ENGLISH_LINGUISTIC = LinguisticResource(
    language_code="en",
    pdf_default_title="Summary",
    help_phrases=(
        "what do you need?",
        "how can i help",
        "how can i assist",
        "i'm here to help",
        "i am here to help",
        "options to help you",
        "please tell me which",
        "let me know what you need",
        "thank you for sharing",
        "based on the provided excerpts",
        "here is a structured synthesis of what you might be looking for",
        "would you like me to continue?",
        "i can continue if you want",
        "what would you like me to do?",
        "here is your summary",
        "let's continue",
        "shall i proceed?",
    ),
    menu_headings=(
        "options to help you",
        "how can i assist",
        "option menu",
        "menu of options",
        "how can i help you today",
    ),
    greeting_prefixes=(
        "hi",
        "hello",
        "hey",
        "greetings",
    ),
    continuation_phrases=(
        "continue...",
        "let's continue",
        "would you like me to continue",
        "shall i continue",
    ),
    intro_heading_regex=r"(?i)^#+\s*(?:1\.\s*)?introduction",
    conclusion_heading_regex=r"(?i)^#+\s*(?:\d+\.\s*)?conclusion",
    final_points_replacement="Final Points",
    toc_markers=(
        "table of contents",
        "table of examples",
        "contents",
        "general index",
        "detailed index",
    ),
    caption_markers=(
        "figure",
        "table",
        "photo",
        "image",
        "chart",
        "diagram",
    ),
    truncated_markers=(
        "[truncated]",
        "...[cut]",
        "[text cut]",
    ),
)
