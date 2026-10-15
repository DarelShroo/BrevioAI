"""Korean linguistic resources for AI pipeline cleaning, quality gates, and postprocessing."""

from __future__ import annotations

from core.brevio.constants.linguistic.base import LinguisticResource

KOREAN_LINGUISTIC = LinguisticResource(
    language_code="ko",
    pdf_default_title="요약",
    help_phrases=(
        "무엇을 도와드릴까요?",
        "도움이 필요하신가요?",
        "계속할까요?",
        "요약본입니다",
        "계속 진행하겠습니다",
    ),
    menu_headings=(
        "도움말 옵션",
        "옵션 메뉴",
    ),
    greeting_prefixes=(
        "안녕하세요",
    ),
    continuation_phrases=(
        "계속...",
        "계속 진행",
    ),
    intro_heading_regex=r"(?i)^#+\s*(?:1\.\s*)?서론|도입",
    conclusion_heading_regex=r"(?i)^#+\s*(?:\d+\.\s*)?결론|맺음말",
    final_points_replacement="최종 요점",
    toc_markers=(
        "목차",
        "차례",
    ),
    caption_markers=(
        "그림",
        "표",
        "사진",
    ),
    truncated_markers=(
        "[텍스트 잘림]",
        "[잘림]",
    ),
)
