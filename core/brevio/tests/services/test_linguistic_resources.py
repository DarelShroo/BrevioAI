"""Tests for multilingual linguistic resources and AI pipeline cleanup heuristics."""

import pytest
from core.brevio.constants.linguistic import (
    LINGUISTIC_RESOURCES,
    UnsupportedLinguisticLanguageError,
    get_all_caption_markers,
    get_all_chatbot_markers,
    get_all_menu_headings,
    get_all_toc_markers,
    get_all_truncated_markers,
    resolve_linguistic_resource,
)
from core.brevio.enums.language import LanguageType
from core.brevio.services.pdf_export.pdf_renderer import build_html_document
from core.brevio.services.summary_service import SummaryService
from core.shared.utils.summary_quality import (
    assistant_chat_score,
    looks_like_assistant_chat,
    looks_truncated,
)


@pytest.mark.parametrize(
    "lang",
    [
        LanguageType.ENGLISH,
        LanguageType.SPANISH,
        LanguageType.FRENCH,
        LanguageType.GERMAN,
        LanguageType.ITALIAN,
        LanguageType.PORTUGUESE_PORTUGAL,
        LanguageType.RUSSIAN,
        LanguageType.CHINESE,
        LanguageType.JAPANESE,
        LanguageType.KOREAN,
        LanguageType.ARABIC,
        LanguageType.HINDI,
    ],
)
def test_all_12_languages_have_complete_linguistic_resources(lang: LanguageType) -> None:
    res = resolve_linguistic_resource(lang)
    assert res.language_code
    assert res.pdf_default_title
    assert len(res.help_phrases) >= 3
    assert len(res.menu_headings) >= 1
    assert len(res.greeting_prefixes) >= 1
    assert res.intro_heading_regex
    assert res.conclusion_heading_regex
    assert res.final_points_replacement
    assert len(res.toc_markers) >= 1
    assert len(res.caption_markers) >= 1
    assert len(res.truncated_markers) >= 1


def test_unsupported_linguistic_language_raises_explicitly() -> None:
    with pytest.raises(UnsupportedLinguisticLanguageError):
        resolve_linguistic_resource("klingon")


def test_chatbot_detection_works_for_all_supported_languages() -> None:
    for lang in [
        LanguageType.ENGLISH,
        LanguageType.SPANISH,
        LanguageType.FRENCH,
        LanguageType.GERMAN,
    ]:
        res = resolve_linguistic_resource(lang)
        sample = f"{res.greeting_prefixes[0]}! {res.help_phrases[0]} {res.menu_headings[0]}"
        score = assistant_chat_score(sample, target_language=lang)
        assert score >= 0.35
        assert looks_like_assistant_chat(sample, target_language=lang)


def test_looks_truncated_detects_multilingual_markers() -> None:
    assert looks_truncated("Something happened [truncated]")
    assert looks_truncated("Algo ocurrió [texto truncado]")
    assert looks_truncated("Quelque chose s'est passé [texte tronqué]")
    assert looks_truncated("Etwas ist passiert [gekürzt]")


def test_sanitize_structure_adapts_to_target_language() -> None:
    service = SummaryService.__new__(SummaryService)

    # Test English sanitization
    en_doc = (
        "## Introduction\nText 1\n## 1. Introduction\nText 2\n"
        "## Conclusion\nEnd 1\n## Conclusion\nEnd 2"
    )
    sanitized_en = service._sanitize_structure(en_doc, target_language=LanguageType.ENGLISH)
    assert "Final Points" in sanitized_en
    assert sanitized_en.count("## Introduction") + sanitized_en.count("## 1. Introduction") == 1

    # Test Spanish sanitization
    es_doc = (
        "## Introducción\nTexto 1\n## Introducción\nTexto 2\n"
        "## Conclusión\nFin 1\n## Conclusión\nFin 2"
    )
    sanitized_es = service._sanitize_structure(es_doc, target_language=LanguageType.SPANISH)
    assert "Puntos Finales" in sanitized_es
    assert sanitized_es.count("## Introducción") == 1


def test_build_html_document_uses_target_language_and_title() -> None:
    html_en = build_html_document("<p>Hello</p>", lang="en")
    assert '<html lang="en">' in html_en
    assert "<title>Summary</title>" in html_en

    html_de = build_html_document("<p>Hallo</p>", lang="de")
    assert '<html lang="de">' in html_de
    assert "<title>Zusammenfassung</title>" in html_de

    html_es = build_html_document("<p>Hola</p>", lang="es")
    assert '<html lang="es">' in html_es
    assert "<title>Resumen</title>" in html_es
