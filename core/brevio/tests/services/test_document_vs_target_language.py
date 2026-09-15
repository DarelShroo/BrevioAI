"""Strict separation between document_language and target_language.

document_language  -> original source content only
target_language    -> all model-bound instructions + expected summary language
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.brevio.constants.prompts import ENGLISH, FRENCH, SPANISH
from core.brevio.enums.language import LanguageType
from core.brevio.enums.role import RoleType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.services.advanced_content_generator import (
    AdvancedPromptGenerator,
    resolve_language_prompts,
)
from core.brevio.services.summary_service import SummaryService
from core.shared.enums.model import ModelType
from core.shared.models.history_token_model import HistoryTokenModel

# Distinctive instruction fingerprints per target language.
TARGET_FINGERPRINTS = {
    LanguageType.ENGLISH: (
        ENGLISH.SPECIFIC_LANGUAGE,
        "Instructions: Extract the distinctive facts from this fragment.",
        "You are an expert editor",
        "You are a formatting editor",
    ),
    LanguageType.SPANISH: (
        SPANISH.SPECIFIC_LANGUAGE,
        "Instrucciones: Extrae los hechos distintivos",
        "Eres un editor experto",
        "Eres un editor de formato",
    ),
    LanguageType.FRENCH: (
        FRENCH.SPECIFIC_LANGUAGE,
        "Instructions : Extraire les faits distinctifs",
        "Vous êtes un éditeur expert",
        "Vous êtes un éditeur de formatage",
    ),
}

# Fingerprints that must NOT appear when another target language is selected.
FOREIGN_INSTRUCTION_MARKERS = {
    LanguageType.ENGLISH: (
        "Eres un editor de formato",
        "Instrucciones: Extrae los hechos distintivos",
        "Vous êtes un éditeur de formatage",
    ),
    LanguageType.SPANISH: (
        "You are a formatting editor",
        "Instructions: Extract the distinctive facts from this fragment.",
        "Vous êtes un éditeur de formatage",
    ),
    LanguageType.FRENCH: (
        "You are a formatting editor",
        "Eres un editor de formato",
        "Instrucciones: Extrae los hechos distintivos",
    ),
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "document_language,target_language,document_excerpt",
    [
        (
            LanguageType.ENGLISH,
            LanguageType.SPANISH,
            "JavaScript is a programming language. Functions are first-class values.",
        ),
        (
            LanguageType.SPANISH,
            LanguageType.ENGLISH,
            "JavaScript es un lenguaje de programación. Las funciones son valores de primera clase.",
        ),
        (
            LanguageType.GERMAN,
            LanguageType.FRENCH,
            "JavaScript ist eine Programmiersprache. Funktionen sind First-Class-Werte.",
        ),
        (
            LanguageType.SPANISH,
            LanguageType.SPANISH,
            "JavaScript es un lenguaje de programación usado en el navegador.",
        ),
    ],
    ids=["en->es", "es->en", "de->fr", "es->es"],
)
async def test_pipeline_prompts_follow_target_not_document_language(
    document_language: LanguageType,
    target_language: LanguageType,
    document_excerpt: str,
) -> None:
    gen = AdvancedPromptGenerator()
    map_prompt = await gen.get_map_prompt(
        target_language, summary_level=SummaryLevel.MODERATE
    )
    reduce_prompt = await gen.get_reduce_prompt(
        target_language, summary_level=SummaryLevel.MODERATE
    )
    direct_prompt = await gen.get_direct_summary_prompt(
        target_language, summary_level=SummaryLevel.MODERATE
    )
    format_prompt = await gen.get_format_prompt(target_language)

    target_module = resolve_language_prompts(target_language)
    directive = AdvancedPromptGenerator.target_language_directive(target_module)

    for blob in (map_prompt, reduce_prompt, direct_prompt, format_prompt):
        assert directive in blob
        assert target_module.SPECIFIC_LANGUAGE in blob
        # Document excerpt must never be embedded into instruction builders.
        assert document_excerpt not in blob

    for marker in TARGET_FINGERPRINTS[target_language]:
        assert any(
            marker in blob
            for blob in (map_prompt, reduce_prompt, direct_prompt, format_prompt)
        ), f"missing target fingerprint {marker!r}"

    for foreign in FOREIGN_INSTRUCTION_MARKERS[target_language]:
        for blob in (map_prompt, reduce_prompt, direct_prompt, format_prompt):
            assert foreign not in blob

    # When languages differ, document-language module text must be absent.
    if document_language != target_language and document_language in (
        LanguageType.ENGLISH,
        LanguageType.SPANISH,
        LanguageType.FRENCH,
        LanguageType.GERMAN,
    ):
        doc_module = resolve_language_prompts(document_language)
        if doc_module.SPECIFIC_LANGUAGE != target_module.SPECIFIC_LANGUAGE:
            for blob in (map_prompt, reduce_prompt, direct_prompt, format_prompt):
                assert doc_module.SPECIFIC_LANGUAGE not in blob


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "document_excerpt,target_language",
    [
        (
            "The quick brown fox jumps over the lazy dog. Chapter 1 explains closures.",
            LanguageType.SPANISH,
        ),
        (
            "El zorro marrón rápido salta sobre el perro perezoso. El capítulo 1 explica closures.",
            LanguageType.ENGLISH,
        ),
        (
            "Der schnelle braune Fuchs springt über den faulen Hund.",
            LanguageType.FRENCH,
        ),
    ],
    ids=["en-content-es-target", "es-content-en-target", "de-content-fr-target"],
)
async def test_map_user_message_preserves_document_language_verbatim(
    document_excerpt: str,
    target_language: LanguageType,
) -> None:
    """SYSTEM = target_language instructions; USER = original document chunk."""
    service = SummaryService()
    service.history_token_model = HistoryTokenModel(
        summary_level=SummaryLevel.MODERATE.value
    )
    service.temperature = 0.0
    service._record_prompt_hash = MagicMock()
    service._record_api_request = MagicMock()
    service._check_token_limit = AsyncMock()
    service.refund_tokens = MagicMock()
    service._quota_scope_and_provider = MagicMock(return_value=("test", "scope"))
    service._map_completion_token_limit = MagicMock(return_value=256)

    captured: dict[str, Any] = {}

    class _Choice:
        finish_reason = "stop"
        message = MagicMock(content="resumen-ok")

    class _Response:
        choices = [_Choice()]
        usage = MagicMock(completion_tokens=12, total_tokens=80)

    async def _execute(call, **kwargs):
        return await call()

    service.provider_executor = MagicMock()
    service.provider_executor.execute = AsyncMock(side_effect=_execute)

    async def fake_create(**kwargs):
        captured["messages"] = kwargs["messages"]
        return _Response()

    client = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=fake_create)
    service.client = client

    map_prompt = await AdvancedPromptGenerator().get_map_prompt(
        target_language, summary_level=SummaryLevel.MODERATE
    )

    with patch(
        "core.brevio.services.summary_service.completion_extra_kwargs",
        return_value={},
    ), patch(
        "core.brevio.services.summary_service.get_encoder",
        return_value=MagicMock(encode=lambda t: list(range(max(1, len(t) // 4)))),
    ), patch(
        "core.brevio.services.summary_service.dump_audit",
    ), patch(
        "core.brevio.services.summary_service.get_model_capabilities",
        return_value=MagicMock(
            native_max_output_tokens=4096,
            context_window=128000,
            overhead=1000,
            output_padding_tokens=64,
            max_tokens_per_chunk=8000,
            min_chunk_tokens=32,
            global_map_safety_cap=8000,
            format_safety_margin=256,
            provider="openai",
        ),
    ):
        await service.generate_summary_chunk(
            index=0,
            chunk=document_excerpt,
            prompt=map_prompt,
            model=ModelType.GPT_4O_MINI,
            target_language=target_language,
            total_document_tokens=200,
            total_chunks=1,
            output_target_tokens=100,
        )

    messages = captured["messages"]
    assert messages[0]["role"] == RoleType.SYSTEM.value
    assert messages[1]["role"] == RoleType.USER.value
    assert messages[1]["content"] == document_excerpt

    system = messages[0]["content"]
    target_module = resolve_language_prompts(target_language)
    assert target_module.SPECIFIC_LANGUAGE in system
    assert document_excerpt not in system


@pytest.mark.asyncio
async def test_reduce_and_format_wrappers_use_target_language_not_document() -> None:
    target = LanguageType.SPANISH
    documentish = "This English paragraph must remain as content payload only."

    reduce_user = resolve_language_prompts(target).get_reduce_user_content(documentish)
    format_user = resolve_language_prompts(target).get_format_user_content(documentish)

    assert documentish in reduce_user
    assert documentish in format_user
    assert reduce_user.startswith("Procesa los siguientes")
    assert "Por favor, aplica el formato" in format_user
    assert "Process the following text blocks" not in reduce_user
    assert "Please apply the format" not in format_user


def test_resolve_language_prompts_is_target_keyed_not_document() -> None:
    """Prompt module selection follows target_language exclusively."""
    assert resolve_language_prompts(LanguageType.SPANISH) is SPANISH
    assert resolve_language_prompts(LanguageType.ENGLISH) is ENGLISH
    assert resolve_language_prompts(LanguageType.FRENCH) is FRENCH
    assert resolve_language_prompts(LanguageType.GERMAN) is not SPANISH


def test_prompt_config_exposes_target_language_alias() -> None:
    from core.brevio.enums.category import CategoryType
    from core.brevio.enums.output_format_type import OutputFormatType
    from core.brevio.models.prompt_config_model import PromptConfig

    cfg = PromptConfig.model_construct(
        model=ModelType.GPT_4O_MINI,
        category=CategoryType.SIMPLE_SUMMARY.value,
        style="default",
        format=OutputFormatType.MARKDOWN,
        language=LanguageType.FRENCH,
        summary_level=SummaryLevel.MODERATE,
    )
    assert cfg.target_language is LanguageType.FRENCH
    assert cfg.target_language is cfg.language
