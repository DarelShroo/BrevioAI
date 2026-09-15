"""Structural and content-parity guards for all LLM prompt language modules.

Canonical sources of truth are Spanish and English (union). Every supported
language must expose the same categories, styles, rule counts, pipeline methods
and MAP/REDUCE structural density so the model receives equivalent instructions.
"""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

import pytest

from core.brevio.constants.prompts import (
    ARABIC,
    CHINESE,
    ENGLISH,
    FRENCH,
    GERMAN,
    HINDI,
    ITALIAN,
    JAPANESE,
    KOREAN,
    PORTUGUESE,
    RUSSIAN,
    SPANISH,
)
from core.brevio.enums.language import LanguageType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.services import summary_service as summary_service_module
from core.brevio.services.advanced_content_generator import AdvancedPromptGenerator

SUPPORTED = [
    (LanguageType.ENGLISH, ENGLISH),
    (LanguageType.SPANISH, SPANISH),
    (LanguageType.GERMAN, GERMAN),
    (LanguageType.FRENCH, FRENCH),
    (LanguageType.ITALIAN, ITALIAN),
    (LanguageType.PORTUGUESE_PORTUGAL, PORTUGUESE),
    (LanguageType.RUSSIAN, RUSSIAN),
    (LanguageType.JAPANESE, JAPANESE),
    (LanguageType.KOREAN, KOREAN),
    (LanguageType.CHINESE, CHINESE),
    (LanguageType.ARABIC, ARABIC),
    (LanguageType.HINDI, HINDI),
]

CANONICAL = SPANISH
CANONICAL_EN = ENGLISH

PIPELINE_METHODS = [
    "get_prompt_base",
    "get_mandatory_rules_prompt",
    "get_map_prompt",
    "get_reduce_prompt",
    "get_available_styles_title",
    "get_semantic_profile_title",
    "get_length_instruction_title",
    "get_semantic_profile",
    "get_length_instruction",
    "get_coverage_guarantee",
    "get_coverage_checklist",
    "get_toc_map_stub",
    "get_map_closing_instruction",
    "get_direct_summary_intro",
    "get_format_prompt",
    "get_format_strict_rules",
    "get_format_user_content",
    "get_format_position_hint",
    "get_reduce_user_content",
    "format_reduce_block_header",
    "get_intermediate_reduce_instruction",
    "get_final_reduce_instruction",
    "get_reduce_quality_retry_instruction",
]

REQUIRED_CATEGORIES = {
    "simple_summary",
    "journalism",
    "marketing",
    "health",
    "technology",
    "education",
    "architecture",
    "finance",
    "tourism",
    "requirements",
    "sciences",
}


def _dash_rules(fn) -> int:
    return inspect.getsource(fn).count("- ")


def _numbered_rules(text: str) -> int:
    return len(re.findall(r"(?m)^\s*\d+\.", text))


@pytest.mark.parametrize(
    "language,instance",
    SUPPORTED,
    ids=[lang.name for lang, _ in SUPPORTED],
)
def test_language_defines_all_pipeline_methods_locally(
    language: LanguageType, instance
) -> None:
    cls = type(instance)
    for name in PIPELINE_METHODS:
        assert name in cls.__dict__, f"{cls.__name__} must define {name} locally"
        assert callable(getattr(instance, name))


@pytest.mark.parametrize(
    "language,instance",
    SUPPORTED,
    ids=[lang.name for lang, _ in SUPPORTED],
)
def test_templates_and_examples_cover_canonical_categories(
    language: LanguageType, instance
) -> None:
    assert set(instance.TEMPLATES.keys()) == REQUIRED_CATEGORIES
    assert set(instance.EXAMPLES.keys()) == REQUIRED_CATEGORIES
    assert set(instance.TEMPLATES.keys()) == set(CANONICAL.TEMPLATES.keys())
    assert set(instance.EXAMPLES.keys()) == set(CANONICAL.EXAMPLES.keys())


@pytest.mark.parametrize(
    "language,instance",
    SUPPORTED,
    ids=[lang.name for lang, _ in SUPPORTED],
)
def test_template_style_and_rule_counts_match_spanish(
    language: LanguageType, instance
) -> None:
    for category, canon_data in CANONICAL.TEMPLATES.items():
        data = instance.TEMPLATES[category]
        assert set(data["styles"].keys()) == set(canon_data["styles"].keys()), category
        assert len(data.get("rules", [])) == len(
            canon_data.get("rules", [])
        ), f"{language.name}/{category} rules"
        for style, canon_style in canon_data["styles"].items():
            style_info = data["styles"][style]
            assert len(style_info.get("elements", [])) == len(
                canon_style.get("elements", [])
            ), f"{language.name}/{category}/{style} elements"
        assert set(instance.EXAMPLES[category].keys()) == set(
            CANONICAL.EXAMPLES[category].keys()
        ), f"{language.name}/{category} examples"


@pytest.mark.parametrize(
    "language,instance",
    SUPPORTED,
    ids=[lang.name for lang, _ in SUPPORTED],
)
def test_map_reduce_mandatory_structural_density(
    language: LanguageType, instance
) -> None:
    assert _dash_rules(instance.get_map_prompt) == _dash_rules(CANONICAL.get_map_prompt)
    assert (
        abs(
            _dash_rules(instance.get_reduce_prompt)
            - _dash_rules(CANONICAL.get_reduce_prompt)
        )
        <= 1
    )
    assert len(instance.get_mandatory_rules_prompt(None)) == 7
    assert len(CANONICAL_EN.get_mandatory_rules_prompt(None)) == 7
    assert _numbered_rules(instance.get_format_strict_rules()) == 12


@pytest.mark.parametrize(
    "language,instance",
    SUPPORTED,
    ids=[lang.name for lang, _ in SUPPORTED],
)
def test_final_and_intermediate_reduce_formulas(
    language: LanguageType, instance
) -> None:
    final_src = inspect.getsource(instance.get_final_reduce_instruction)
    inter_src = inspect.getsource(instance.get_intermediate_reduce_instruction)
    assert "0.55" in final_src
    assert "0.80" in inter_src or "0.8" in inter_src
    final_text = instance.get_final_reduce_instruction(2000)
    inter_text = instance.get_intermediate_reduce_instruction(4000, 0.45)
    assert "825" in final_text or "1500" in final_text
    assert "1350" in inter_text or "1080" in inter_text
    retry = instance.get_reduce_quality_retry_instruction()
    assert retry.strip()
    assert retry.endswith("\n\n") or "\n" in retry


@pytest.mark.parametrize(
    "language,instance",
    SUPPORTED,
    ids=[lang.name for lang, _ in SUPPORTED],
)
def test_semantic_and_length_cover_all_summary_levels(
    language: LanguageType, instance
) -> None:
    for level in SummaryLevel:
        semantic = instance.get_semantic_profile(level)
        length = instance.get_length_instruction(level)
        assert semantic.strip(), f"{language.name} semantic {level}"
        assert length.strip(), f"{language.name} length {level}"
    # VERY_DETAILED must keep the technical-tutorial extras present in ES/EN.
    vd = instance.get_semantic_profile(SummaryLevel.VERY_DETAILED)
    detailed = instance.get_semantic_profile(SummaryLevel.DETAILED)
    assert len(vd) > len(
        detailed
    ), f"{language.name} VERY_DETAILED must add tutorial extras"


@pytest.mark.parametrize(
    "language,instance",
    SUPPORTED,
    ids=[lang.name for lang, _ in SUPPORTED],
)
def test_direct_intro_and_coverage_checklist_are_substantive(
    language: LanguageType, instance
) -> None:
    intro = instance.get_direct_summary_intro()
    assert len(intro) >= 100
    checklist = instance.get_coverage_checklist(["Section A", "Section B"])
    assert "Section A" in checklist
    assert "Section B" in checklist
    user = instance.get_reduce_user_content("BATCH")
    assert "BATCH" in user
    assert len(user) > len("BATCH") + 20


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "language,instance",
    SUPPORTED,
    ids=[lang.name for lang, _ in SUPPORTED],
)
async def test_composed_final_prompts_include_canonical_blocks(
    language: LanguageType, instance
) -> None:
    gen = AdvancedPromptGenerator()
    map_prompt = await gen.get_map_prompt(language, summary_level=SummaryLevel.MODERATE)
    reduce_prompt = await gen.get_reduce_prompt(
        language, summary_level=SummaryLevel.MODERATE
    )
    direct_prompt = await gen.get_direct_summary_prompt(
        language, summary_level=SummaryLevel.MODERATE
    )
    format_prompt = await gen.get_format_prompt(language)

    directive = AdvancedPromptGenerator.target_language_directive(instance)
    assert directive in map_prompt
    assert directive in reduce_prompt
    assert directive in direct_prompt
    assert directive in format_prompt

    assert instance.get_map_closing_instruction() in map_prompt
    assert instance.get_length_instruction(SummaryLevel.MODERATE) in map_prompt
    assert instance.get_coverage_guarantee() in reduce_prompt
    assert instance.get_direct_summary_intro() in direct_prompt
    assert instance.get_format_prompt() in format_prompt

    # MAP/REDUCE bodies must be the dense canonical versions, not the old 7-bullet stubs.
    assert _dash_rules(instance.get_map_prompt) >= 23
    assert _dash_rules(instance.get_reduce_prompt) >= 17


def test_english_and_spanish_mandatory_rules_are_union() -> None:
    assert len(ENGLISH.get_mandatory_rules_prompt(None)) == 7
    assert len(SPANISH.get_mandatory_rules_prompt(None)) == 7


def test_summary_service_uses_i18n_quality_retry_not_hardcoded_english() -> None:
    source = Path(summary_service_module.__file__).read_text(encoding="utf-8")
    assert "get_reduce_quality_retry_instruction" in source
    literals: list[str] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.append(node.value)
        elif isinstance(node, ast.JoinedStr):
            for part in node.values:
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    literals.append(part.value)
    joined = "\n".join(literals)
    assert "Never a help menu, assistant greeting" not in joined
    assert "CRITICAL: Write the summary itself" not in joined


def test_sciences_and_requirements_present_in_english_catalog() -> None:
    gen = AdvancedPromptGenerator()
    templates = gen.get_available_templates()
    assert "sciences" in templates
    assert "requirements" in templates
    assert "elicitation" in templates["requirements"]
    assert "guide" in templates["sciences"]
