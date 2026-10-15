"""Arabic linguistic resources for AI pipeline cleaning, quality gates, and postprocessing."""

from __future__ import annotations

from core.brevio.constants.linguistic.base import LinguisticResource

ARABIC_LINGUISTIC = LinguisticResource(
    language_code="ar",
    pdf_default_title="الملخص",
    help_phrases=(
        "ماذا تحتاج؟",
        "كيف يمكنني مساعدتك",
        "هل تريد مني أن أستمر؟",
        "هل يمكنني المتابعة؟",
        "إليك الملخص",
        "دعنا نستمر",
    ),
    menu_headings=(
        "خيارات المساعدة",
        "قائمة الخيارات",
    ),
    greeting_prefixes=(
        "مرحبا",
        "أهلا",
        "السلام عليكم",
    ),
    continuation_phrases=(
        "متابعة...",
        "للمتابعة",
        "استمرار",
    ),
    intro_heading_regex=r"(?i)^#+\s*(?:1\.\s*)?مقدمة|المقدمة",
    conclusion_heading_regex=r"(?i)^#+\s*(?:\d+\.\s*)?خاتمة|الخاتمة",
    final_points_replacement="النقاط الختامية",
    toc_markers=(
        "فهرس",
        "جدول المحتويات",
        "قائمة المحتويات",
    ),
    caption_markers=(
        "شكل",
        "جدول",
        "صورة",
    ),
    truncated_markers=(
        "[تم قطع النص]",
        "[مقطوع]",
    ),
)
