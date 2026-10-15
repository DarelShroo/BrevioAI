"""Russian linguistic resources for AI pipeline cleaning, quality gates, and postprocessing."""

from __future__ import annotations

from core.brevio.constants.linguistic.base import LinguisticResource

RUSSIAN_LINGUISTIC = LinguisticResource(
    language_code="ru",
    pdf_default_title="Резюме",
    help_phrases=(
        "чем я могу помочь",
        "что вам нужно?",
        "я здесь, чтобы помочь",
        "хотите, чтобы я продолжил?",
        "могу ли я продолжить?",
        "вот ваше резюме",
        "давайте продолжим",
    ),
    menu_headings=(
        "варианты помощи",
        "меню параметров",
        "чем я могу помочь вам сегодня",
    ),
    greeting_prefixes=(
        "привет",
        "здравствуйте",
        "добрый день",
    ),
    continuation_phrases=(
        "продолжить...",
        "давайте продолжим",
        "продолжаем",
    ),
    intro_heading_regex=r"(?i)^#+\s*(?:1\.\s*)?введение",
    conclusion_heading_regex=r"(?i)^#+\s*(?:\d+\.\s*)?заключение|вывод",
    final_points_replacement="Заключительные пункты",
    toc_markers=(
        "содержание",
        "оглавление",
        "список таблиц",
    ),
    caption_markers=(
        "рисунок",
        "таблица",
        "фото",
        "иллюстрация",
    ),
    truncated_markers=(
        "[текст обрезан]",
        "[обрезано]",
    ),
)
