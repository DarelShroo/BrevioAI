"""Hindi linguistic resources for AI pipeline cleaning, quality gates, and postprocessing."""

from __future__ import annotations

from core.brevio.constants.linguistic.base import LinguisticResource

HINDI_LINGUISTIC = LinguisticResource(
    language_code="hi",
    pdf_default_title="सारांश",
    help_phrases=(
        "आपको क्या चाहिए?",
        "मैं आपकी क्या मदद कर सकता हूँ?",
        "क्या आप चाहते हैं कि मैं जारी रखूँ?",
        "यहाँ आपका सारांश है",
        "आइए जारी रखें",
    ),
    menu_headings=(
        "सहायता विकल्प",
        "विकल्प मेनू",
    ),
    greeting_prefixes=(
        "नमस्ते",
        "नमस्कार",
    ),
    continuation_phrases=(
        "जारी रखें...",
        "आगे बढ़ें",
    ),
    intro_heading_regex=r"(?i)^#+\s*(?:1\.\s*)?प्रस्तावना|परिचय",
    conclusion_heading_regex=r"(?i)^#+\s*(?:\d+\.\s*)?निष्कर्ष|उपसंहार",
    final_points_replacement="अंतिम बिंदु",
    toc_markers=(
        "विषय-सूची",
        "सामग्री",
        "अनुक्रमणिका",
    ),
    caption_markers=(
        "चित्र",
        "तालिका",
        "फ़ोटो",
    ),
    truncated_markers=(
        "[काटा गया पाठ]",
        "[छोटा किया गया]",
    ),
)
