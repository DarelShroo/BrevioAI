"""Guarantee model-bound prompts come only from the selected language module."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from core.brevio.constants import prompts as prompts_pkg
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
from core.brevio.services.advanced_content_generator import (
    PROMPT_LANGUAGES,
    AdvancedPromptGenerator,
    UnsupportedPromptLanguageError,
    resolve_language_prompts,
)

PIPELINE_SERVICE_FILES = [
    Path(summary_service_module.__file__),
    Path(__file__).resolve().parents[2] / "services" / "advanced_content_generator.py",
]

FORBIDDEN_SERVICE_PROMPT_SNIPPETS = [
    "CRITICAL FORMATTING RULES",
    "Por favor, aplica el formato",
    "Procesa los siguientes bloques de texto",
    "IMPORTANT: This is BLOCK",
    "You are a formatting editor",
    "Eres un editor de formato",
    "CRITICAL INSTRUCTION: You are an intermediate",
    "CRITICAL INSTRUCTION: You are the FINAL",
    "COVERAGE GUARANTEE (applies at every summary level)",
    "Perfil Semántico (Información a Preservar)",
    "Instrucción de cierre",
    "ABDECKUNGSGARANTIE",
    "GARANTIE DE COUVERTURE",
    "CRITICAL: Write the summary itself",
    "Never a help menu, assistant greeting",
]

SUPPORTED_LANG_INSTANCES = [
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

REQUIRED_METHODS = [
    "get_format_prompt",
    "get_format_strict_rules",
    "get_format_user_content",
    "get_format_position_hint",
    "get_reduce_user_content",
    "format_reduce_block_header",
    "get_coverage_guarantee",
    "get_coverage_checklist",
    "get_toc_map_stub",
    "get_semantic_profile",
    "get_length_instruction",
    "get_map_closing_instruction",
    "get_direct_summary_intro",
    "get_intermediate_reduce_instruction",
    "get_final_reduce_instruction",
    "get_reduce_quality_retry_instruction",
    "get_map_prompt",
    "get_reduce_prompt",
]

# Distinctive fingerprints that must appear for each language's format prompt
# and must not appear when another language is selected.
LANGUAGE_FINGERPRINTS = {
    LanguageType.ENGLISH: "You are a formatting editor",
    LanguageType.SPANISH: "Eres un editor de formato",
    LanguageType.GERMAN: "Sie sind ein Formatierungsredakteur",
    LanguageType.FRENCH: "Vous êtes un éditeur de formatage",
    LanguageType.ITALIAN: "Sei un editor di formattazione",
    LanguageType.PORTUGUESE_PORTUGAL: "É um editor de formatação",
    LanguageType.RUSSIAN: "Вы редактор форматирования",
    LanguageType.JAPANESE: "あなたはフォーマット編集者です",
    LanguageType.KOREAN: "당신은 포맷 편집자입니다",
    LanguageType.CHINESE: "你是格式编辑",
    LanguageType.ARABIC: "أنت محرر تنسيق",
    LanguageType.HINDI: "आप प्रारूप संपादक हैं",
}


def _string_literals(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            values.append(node.value)
        elif isinstance(node, ast.JoinedStr):
            for part in node.values:
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    values.append(part.value)
    return values


@pytest.mark.parametrize("path", PIPELINE_SERVICE_FILES, ids=lambda p: p.name)
def test_pipeline_services_contain_no_hardcoded_model_prompts(path: Path) -> None:
    literals = "\n".join(_string_literals(path))
    for snippet in FORBIDDEN_SERVICE_PROMPT_SNIPPETS:
        assert (
            snippet not in literals
        ), f"{path.name} still hardcodes model-bound text: {snippet!r}"


def test_no_base_language_prompts_module() -> None:
    prompts_dir = Path(prompts_pkg.__file__).resolve().parent
    assert not (prompts_dir / "base.py").exists()
    for name in prompts_dir.glob("*.py"):
        if name.name.startswith("_"):
            continue
        src = name.read_text(encoding="utf-8")
        assert "BaseLanguagePrompts" not in src
        assert "prompts.base" not in src


@pytest.mark.parametrize(
    "language,instance",
    SUPPORTED_LANG_INSTANCES,
    ids=[lang.name for lang, _ in SUPPORTED_LANG_INSTANCES],
)
def test_each_language_defines_pipeline_methods_on_its_own_class(
    language: LanguageType, instance
) -> None:
    cls = type(instance)
    assert "BaseLanguagePrompts" not in {b.__name__ for b in cls.__mro__}
    for name in REQUIRED_METHODS:
        assert name in cls.__dict__, f"{cls.__name__} must define {name} locally"
        assert callable(getattr(instance, name))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "language,instance",
    SUPPORTED_LANG_INSTANCES,
    ids=[lang.name for lang, _ in SUPPORTED_LANG_INSTANCES],
)
async def test_all_pipeline_phases_use_selected_language_only(
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

    own_fp = LANGUAGE_FINGERPRINTS[language]
    assert own_fp in format_prompt
    assert instance.get_map_closing_instruction() in map_prompt
    assert instance.get_length_instruction(SummaryLevel.MODERATE) in map_prompt
    assert instance.get_coverage_guarantee() in reduce_prompt
    assert instance.get_direct_summary_intro() in direct_prompt
    directive = AdvancedPromptGenerator.target_language_directive(instance)
    assert directive in map_prompt
    assert directive in reduce_prompt
    assert directive in direct_prompt
    assert directive in format_prompt
    assert instance.get_format_prompt() in format_prompt
    assert format_prompt.startswith(directive.split("\n")[0])

    # No cross-language fingerprint leakage into FORMAT (instruction language).
    for other_lang, other_fp in LANGUAGE_FINGERPRINTS.items():
        if other_lang == language:
            continue
        assert other_fp not in format_prompt
        assert other_fp not in map_prompt
        assert other_fp not in reduce_prompt
        assert other_fp not in direct_prompt


@pytest.mark.asyncio
async def test_german_execution_never_sends_spanish_or_english_instructions() -> None:
    gen = AdvancedPromptGenerator()
    map_p = await gen.get_map_prompt(
        LanguageType.GERMAN, summary_level=SummaryLevel.DETAILED
    )
    reduce_p = await gen.get_reduce_prompt(
        LanguageType.GERMAN, summary_level=SummaryLevel.DETAILED
    )
    fmt = await gen.get_format_prompt(LanguageType.GERMAN)
    direct = await gen.get_direct_summary_prompt(
        LanguageType.GERMAN, summary_level=SummaryLevel.DETAILED
    )
    intermediate = GERMAN.get_intermediate_reduce_instruction(4000, 0.5)
    final = GERMAN.get_final_reduce_instruction(2000)

    for blob in (map_p, reduce_p, fmt, direct, intermediate, final):
        assert "You are a formatting editor" not in blob
        assert "Eres un editor de formato" not in blob
        assert "CRITICAL FORMATTING RULES" not in blob
        assert "REGLAS CRÍTICAS DE FORMATO" not in blob
        assert "Summarize the following" not in blob
        assert "Por favor, aplica el formato" not in blob
    assert "Formatierungsredakteur" in fmt or "Formatierung" in fmt
    assert "ABDECKUNGSGARANTIE" in reduce_p


@pytest.mark.asyncio
async def test_spanish_execution_uses_spanish_in_all_phases() -> None:
    gen = AdvancedPromptGenerator()
    map_p = await gen.get_map_prompt(
        LanguageType.SPANISH, summary_level=SummaryLevel.MODERATE
    )
    reduce_p = await gen.get_reduce_prompt(
        LanguageType.SPANISH, summary_level=SummaryLevel.MODERATE
    )
    fmt = await gen.get_format_prompt(LanguageType.SPANISH)
    assert "Eres un editor de formato" in fmt
    assert SPANISH.get_map_closing_instruction() in map_p
    assert SPANISH.get_coverage_guarantee() in reduce_p
    assert "You are a formatting editor" not in fmt
    assert "COVERAGE GUARANTEE" not in reduce_p


def test_unsupported_language_raises_instead_of_falling_back() -> None:
    with pytest.raises(UnsupportedPromptLanguageError):
        resolve_language_prompts(LanguageType.POLISH)
    with pytest.raises(UnsupportedPromptLanguageError):
        resolve_language_prompts("xx-unsupported")


def test_resolve_language_prompts_covers_all_prompt_modules() -> None:
    for language, instance in SUPPORTED_LANG_INSTANCES:
        assert resolve_language_prompts(language) is instance
        assert resolve_language_prompts(language.value) is instance
    assert LanguageType.GERMAN.name in PROMPT_LANGUAGES
    assert PROMPT_LANGUAGES[LanguageType.GERMAN.name] is GERMAN


def test_summary_service_never_resolves_prompts_from_language_input() -> None:
    """Static guard: document language must not select prompt modules."""
    source = Path(summary_service_module.__file__).read_text(encoding="utf-8")
    assert (
        "resolve_language_prompts(self.history_token_model.language_input)"
        not in source
    )
    assert "resolve_language_prompts(language_input)" not in source
    assert "resolve_language_prompts(detected_language)" not in source
    # Prompt resolution in the document pipeline must use target_language.
    assert "resolve_language_prompts(target_language)" in source


def test_summary_service_does_not_define_inline_prompt_builders() -> None:
    source = inspect.getsource(summary_service_module.SummaryService)
    assert "CRITICAL FORMATTING RULES" not in source
    assert "Por favor, aplica el formato" not in source
    assert "Procesa los siguientes bloques" not in source
    assert "You are a formatting editor" not in source
