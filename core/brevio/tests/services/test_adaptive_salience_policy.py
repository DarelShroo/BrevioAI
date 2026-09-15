import pytest

from core.brevio.enums.language import LanguageType
from core.brevio.enums.summary_level import SummaryLevel
from core.shared.enums.model import ModelType
from core.shared.utils.adaptive_salience_policy import (
    AdaptiveSaliencePolicy,
    final_reduce_instruction,
    intermediate_reduce_instruction,
)


def test_adaptive_salience_policy_monotonicity():
    policy = AdaptiveSaliencePolicy()
    model = ModelType.GPT_4O_MINI
    # Stay below native_max so higher levels are not all clipped to the same cap.
    doc_tokens = 12000

    levels = [
        SummaryLevel.VERY_CONCISE,
        SummaryLevel.CONCISE,
        SummaryLevel.MODERATE,
        SummaryLevel.DETAILED,
        SummaryLevel.VERY_DETAILED,
    ]

    budgets = [
        policy.budget(model, level, doc_tokens, LanguageType.ENGLISH)
        for level in levels
    ]

    for i in range(len(budgets) - 1):
        assert budgets[i].output_target_tokens <= budgets[i + 1].output_target_tokens
        # When both levels hit the same ceiling (native max or doc+padding),
        # targets may plateau without violating monotonicity.
        next_budget = budgets[i + 1]
        at_hard_cap = next_budget.output_target_tokens >= next_budget.output_hard_limit
        at_doc_cap = next_budget.output_target_tokens >= doc_tokens
        if not at_hard_cap and not at_doc_cap:
            assert budgets[i].output_target_tokens < next_budget.output_target_tokens


def test_adaptive_salience_policy_small_doc_bypass():
    policy = AdaptiveSaliencePolicy()
    model = ModelType.GPT_4O_MINI
    doc_tokens = 1500  # Should be direct route

    decision = policy.budget(
        model, SummaryLevel.MODERATE, doc_tokens, LanguageType.ENGLISH
    )
    assert decision.route == "direct"
    assert decision.requires_hierarchical_reduce is False


def test_medium_doc_uses_map_even_when_context_fits():
    policy = AdaptiveSaliencePolicy()
    model = ModelType.GPT_4O_MINI
    doc_tokens = 10000

    decision = policy.budget(
        model, SummaryLevel.VERY_DETAILED, doc_tokens, LanguageType.SPANISH
    )
    assert decision.route == "hierarchical"
    assert decision.requires_hierarchical_reduce is True
    policy = AdaptiveSaliencePolicy()
    # GPT-4 8k context cannot fit a 6k-token document + output in one pass.
    model = ModelType.GPT_4
    doc_tokens = 6000

    decision = policy.budget(
        model, SummaryLevel.MODERATE, doc_tokens, LanguageType.ENGLISH
    )
    assert decision.route == "hierarchical"
    assert decision.requires_hierarchical_reduce is True


def test_adaptive_salience_policy_caps_native_max():
    policy = AdaptiveSaliencePolicy()
    model = ModelType.GPT_4O_MINI
    doc_tokens = 2000000  # Huge document

    decision = policy.budget(
        model, SummaryLevel.VERY_DETAILED, doc_tokens, LanguageType.ENGLISH
    )
    # output_max_tokens (per call) must not exceed the per-call hard limit.
    # The document artifact target MAY exceed that limit via section assembly.
    assert decision.output_max_tokens <= decision.output_hard_limit
    if decision.output_target_tokens > decision.output_hard_limit:
        assert decision.requires_section_assembly is True
    else:
        assert decision.output_target_tokens <= decision.output_hard_limit


def test_spanish_intermediate_reduce_instruction_targets_remaining_ratio_not_a_maximum():
    prompt = intermediate_reduce_instruction(6000, 0.45, language=LanguageType.SPANISH)
    lowered = prompt.lower()
    assert "aproximadamente el 45%" in lowered
    assert "al menos" in lowered
    assert "cada bloque" in lowered
    prompt = intermediate_reduce_instruction(6000, 0.45, language=LanguageType.ENGLISH)
    lowered = prompt.lower()
    assert "approximately 45%" in lowered
    assert "do not compress substantially below" in lowered
    assert "every block" in lowered
    assert "heavily" not in lowered
    assert "maximum " not in lowered


def test_final_reduce_instruction_preserves_material_when_input_is_shorter():
    prompt = final_reduce_instruction(7288, language=LanguageType.ENGLISH)
    assert "5466" in prompt
    assert "Coverage floor" in prompt or "approximately" in prompt
    assert "do not compress further" in prompt
    assert "do not invent filler" in prompt
    assert "heavily" not in prompt.lower()


def test_spanish_final_reduce_uses_numeric_coverage_floor():
    prompt = final_reduce_instruction(7288, language=LanguageType.SPANISH)
    assert "5466" in prompt
    assert "3006" in prompt or "relleno" in prompt.lower()
    assert "DETENTE" not in prompt


def test_very_concise_instructions_are_not_destructive():
    policy = AdaptiveSaliencePolicy()
    text = policy.length_instructions(LanguageType.ENGLISH)[
        SummaryLevel.VERY_CONCISE
    ].lower()
    assert "absolute minimum" not in text
    assert "extremely short" not in text
    assert "condensed" in text or "dense" in text
    assert "shorter than moderate" in text
    es = policy.length_instructions(LanguageType.SPANISH)[SummaryLevel.VERY_CONCISE]
    assert "más corto" in es.lower()
    assert "secundari" in es.lower()


def test_budget_decision_texts_follow_selected_language():
    policy = AdaptiveSaliencePolicy()
    de = policy.budget(
        ModelType.GPT_4O_MINI, SummaryLevel.MODERATE, 5000, LanguageType.GERMAN
    )
    es = policy.budget(
        ModelType.GPT_4O_MINI, SummaryLevel.MODERATE, 5000, LanguageType.SPANISH
    )
    assert "ABDECKUNGSGARANTIE" in de.coverage_instruction
    assert "GARANTÍA DE COBERTURA" in es.coverage_instruction
    assert de.coverage_instruction != es.coverage_instruction
    assert "Länge" in de.length_instruction or "LÄNGE" in de.length_instruction
    assert "LONGITUD" in es.length_instruction


def test_budget_18k_70k_200k_qwen_section_assembly():
    """Document target may exceed a single 8k call; per-call cap stays native."""
    policy = AdaptiveSaliencePolicy()
    model = ModelType.QWEN3_14B
    moderate_18k = policy.budget(
        model, SummaryLevel.MODERATE, 18_000, LanguageType.SPANISH
    )
    moderate_70k = policy.budget(
        model, SummaryLevel.MODERATE, 70_617, LanguageType.SPANISH
    )
    moderate_200k = policy.budget(
        model, SummaryLevel.MODERATE, 200_000, LanguageType.SPANISH
    )

    assert moderate_18k.output_max_tokens <= moderate_18k.output_hard_limit <= 8192
    assert (
        moderate_18k.output_target_tokens <= 8192
        or moderate_18k.requires_section_assembly
    )
    # 70k * 0.28 retention ≈ 19k > 8192
    assert moderate_70k.output_target_tokens > 8192
    assert moderate_70k.requires_section_assembly is True
    assert moderate_70k.output_max_tokens <= 8192
    assert moderate_200k.output_target_tokens > moderate_70k.output_target_tokens
    assert moderate_200k.requires_section_assembly is True
    assert moderate_70k.output_min_tokens > 4000
    assert moderate_70k.output_min_tokens < moderate_70k.output_target_tokens


def test_flash_summary_call_cap_is_not_384k():
    from core.shared.utils.model_capabilities import (
        get_model_capabilities,
        summary_max_output_tokens,
    )

    caps = get_model_capabilities(ModelType.DEEPSEEK_FLASH)
    assert caps.native_max_output_tokens == 384_000
    assert summary_max_output_tokens(caps) == 16_384
    policy = AdaptiveSaliencePolicy()
    decision = policy.budget(
        ModelType.DEEPSEEK_FLASH, SummaryLevel.MODERATE, 70_000, LanguageType.ENGLISH
    )
    assert decision.output_hard_limit == 16_384
    assert decision.output_max_tokens <= 16_384
