import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.brevio.enums.summary_level import SummaryLevel
from core.shared.enums.model import ModelType
from core.shared.utils.model_capabilities import (
    ModelCapabilities,
    get_model_capabilities,
    packing_token_multiplier,
    summary_max_output_tokens,
)

if TYPE_CHECKING:
    from core.brevio.enums.language import LanguageType
    from core.brevio.protocols.language_prompt_protocol import LanguagePromptProtocol

INTERMEDIATE_COMPRESSION_RATIO = 0.55
SECTION_KEEP_RATIO = 0.75
# API max_tokens must sit above the instruction target so filling the target is not
# classified as finish_reason=length / output_tokens >= max_tokens.
REDUCE_COMPLETION_HEADROOM = 1.35
MAP_COMPLETION_HEADROOM = 1.35
FINAL_REDUCE_PACK_CAP = 24_000
MIN_USABLE_MAP_WORDS = 8

# Minimum fraction of source tokens that must remain available as an output floor.
# Controls density, never permits "delete everything until tiny".
_LEVEL_MIN_RETENTION = {
    SummaryLevel.VERY_CONCISE: 0.12,
    SummaryLevel.CONCISE: 0.18,
    SummaryLevel.MODERATE: 0.28,
    SummaryLevel.DETAILED: 0.40,
    SummaryLevel.VERY_DETAILED: 0.55,
}


def _resolve_prompts(target_language: "LanguageType") -> "LanguagePromptProtocol":
    """Resolve prompt texts by target/output language, never document language."""
    from core.brevio.services.advanced_content_generator import resolve_language_prompts

    return resolve_language_prompts(target_language)


def intermediate_reduce_instruction(
    batch_input_tokens: int,
    remaining_ratio: float = INTERMEDIATE_COMPRESSION_RATIO,
    *,
    language: "LanguageType",
) -> str:
    """Model-bound intermediate REDUCE instruction for the target language."""
    return _resolve_prompts(language).get_intermediate_reduce_instruction(
        batch_input_tokens, remaining_ratio
    )


def final_reduce_instruction(
    target_max_tokens: int,
    *,
    language: "LanguageType",
) -> str:
    """Model-bound final REDUCE instruction for the target language."""
    return _resolve_prompts(language).get_final_reduce_instruction(target_max_tokens)


@dataclass(frozen=True)
class MapOutputPolicy:
    max_output_to_input_ratio: float


MAP_POLICIES = {
    SummaryLevel.VERY_CONCISE: MapOutputPolicy(
        max_output_to_input_ratio=0.40,
    ),
    SummaryLevel.CONCISE: MapOutputPolicy(
        max_output_to_input_ratio=0.50,
    ),
    SummaryLevel.MODERATE: MapOutputPolicy(
        max_output_to_input_ratio=0.70,
    ),
    SummaryLevel.DETAILED: MapOutputPolicy(
        max_output_to_input_ratio=1.00,
    ),
    SummaryLevel.VERY_DETAILED: MapOutputPolicy(
        max_output_to_input_ratio=1.50,
    ),
}


@dataclass(frozen=True)
class SummaryPolicyDecision:
    level: SummaryLevel
    semantic_profile: str
    length_instruction: str
    coverage_instruction: str
    output_min_tokens: int
    output_target_tokens: int
    output_max_tokens: int
    output_hard_limit: int
    route: str  # "direct" or "hierarchical"
    requires_hierarchical_reduce: bool
    requires_section_assembly: bool
    section_keep_ratio: float


class AdaptiveSaliencePolicy:
    """
    Adaptive Salience Policy for generating summary budgets.

    Model-bound semantic/length/coverage texts live in the language prompt modules.
    This class owns numeric budgets and routing; text fields require an explicit language.
    """

    @staticmethod
    def calculate_map_safety_ceiling(
        chunk_input_tokens: int,
        summary_level: SummaryLevel,
        capabilities: ModelCapabilities,
    ) -> int:
        policy = MAP_POLICIES.get(summary_level, MAP_POLICIES[SummaryLevel.MODERATE])
        ratio_based_limit = math.ceil(
            chunk_input_tokens * policy.max_output_to_input_ratio
        )
        return min(
            ratio_based_limit,
            summary_max_output_tokens(capabilities),
            capabilities.global_map_safety_cap,
        )

    def __init__(self) -> None:
        # Scale factors for T^0.62 — denser levels produce longer targets.
        self.level_scales = {
            SummaryLevel.VERY_CONCISE: 14.0,
            SummaryLevel.CONCISE: 20.0,
            SummaryLevel.MODERATE: 28.0,
            SummaryLevel.DETAILED: 38.0,
            SummaryLevel.VERY_DETAILED: 50.0,
        }

    def budget(
        self,
        model: ModelType,
        summary_level: SummaryLevel,
        document_tokens: int,
        language: "LanguageType",
    ) -> SummaryPolicyDecision:
        """Compute budgets. ``language`` is target/output language for model-bound texts."""
        if document_tokens <= 0:
            document_tokens = 1

        capabilities = get_model_capabilities(model)
        per_call_cap = summary_max_output_tokens(capabilities)

        scale_factor = self.level_scales.get(summary_level, 28.0)

        # T^0.62 scales better with long documents than T^0.55 (avoids 1-page collapse).
        base_target = int(scale_factor * math.pow(document_tokens, 0.62))
        retention_floor = int(
            document_tokens * _LEVEL_MIN_RETENTION.get(summary_level, 0.28)
        )
        # Soft absolute floors so short/medium docs still keep usable coverage.
        absolute_floor = {
            SummaryLevel.VERY_CONCISE: 400,
            SummaryLevel.CONCISE: 700,
            SummaryLevel.MODERATE: 1100,
            SummaryLevel.DETAILED: 1600,
            SummaryLevel.VERY_DETAILED: 2200,
        }.get(summary_level, 1100)

        ideal_target = max(base_target, retention_floor, absolute_floor)

        # Per-level soft caps vs source size keep levels distinguishable while
        # preventing "copy the whole document" for concise modes.
        input_fraction_cap = {
            SummaryLevel.VERY_CONCISE: 0.40,
            SummaryLevel.CONCISE: 0.55,
            SummaryLevel.MODERATE: 0.70,
            SummaryLevel.DETAILED: 0.90,
            SummaryLevel.VERY_DETAILED: 1.15,
        }.get(summary_level, 0.70)
        size_cap = (
            int(document_tokens * input_fraction_cap)
            + capabilities.output_padding_tokens
        )

        # Document-level artifact target is NOT clipped to a single-call max.
        # Large books are assembled from section syntheses.
        artifact_target = min(ideal_target, size_cap)
        artifact_target = max(artifact_target, min(absolute_floor, size_cap))

        output_min_tokens = max(
            capabilities.min_chunk_tokens,
            int(artifact_target * 0.55),
            min(absolute_floor, artifact_target),
        )
        call_target = min(artifact_target, per_call_cap)
        output_max_tokens = min(
            per_call_cap,
            int(call_target * 1.45) + capabilities.output_padding_tokens,
        )

        available_input = (
            capabilities.context_window - capabilities.overhead - output_max_tokens
        )
        if packing_token_multiplier(capabilities) > 1.0:
            available_input = int(
                available_input / packing_token_multiplier(capabilities)
            )
        # DIRECT only for a single MAP-sized chunk. A document that merely fits
        # in context still needs MAP: long-context 8B models skip the source
        # and emit a generic tutorial instead of covering the actual sections.
        fits_in_context = document_tokens <= int(available_input * 0.90)
        single_chunk = document_tokens <= capabilities.max_tokens_per_chunk
        is_direct = (
            single_chunk
            and fits_in_context
            and available_input > capabilities.min_chunk_tokens
        )
        requires_section_assembly = (not is_direct) and artifact_target > per_call_cap

        prompts = _resolve_prompts(language)
        return SummaryPolicyDecision(
            level=summary_level,
            semantic_profile=prompts.get_semantic_profile(summary_level),
            length_instruction=prompts.get_length_instruction(summary_level),
            coverage_instruction=prompts.get_coverage_guarantee(),
            output_min_tokens=output_min_tokens,
            output_target_tokens=artifact_target,
            output_max_tokens=output_max_tokens,
            output_hard_limit=per_call_cap,
            route="direct" if is_direct else "hierarchical",
            requires_hierarchical_reduce=not is_direct,
            requires_section_assembly=requires_section_assembly,
            section_keep_ratio=SECTION_KEEP_RATIO
            if requires_section_assembly
            else INTERMEDIATE_COMPRESSION_RATIO,
        )

    def semantic_profiles(self, language: "LanguageType"):
        prompts = _resolve_prompts(language)
        return {level: prompts.get_semantic_profile(level) for level in SummaryLevel}

    def length_instructions(self, language: "LanguageType"):
        prompts = _resolve_prompts(language)
        return {level: prompts.get_length_instruction(level) for level in SummaryLevel}
