import math
from dataclasses import dataclass

from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.summary_level import SummaryLevel
from core.shared.enums.model import ModelType
from core.shared.utils.model_capabilities import get_model_capabilities


@dataclass(frozen=True)
class OutputTokenBudget:
    minimum: int
    expected: int
    maximum: int


class OutputTokenPolicy:
    """Deterministic output budget policy shared by execution and estimation."""

    def __init__(self, tokens_per_word: float = 1.35) -> None:
        self.tokens_per_word = tokens_per_word
        self.format_multiplier = {
            OutputFormatType.TEXT: 1.0,
            OutputFormatType.MARKDOWN: 1.10,
            OutputFormatType.JSON: 1.25,
            OutputFormatType.HTML: 1.15,
        }

    def contractual_max_output_tokens(self, model: ModelType) -> int:
        capabilities = get_model_capabilities(model)
        return capabilities.native_max_output_tokens

    def budget(
        self,
        model: ModelType,
        summary_level: SummaryLevel,
        output_format: OutputFormatType,
        style: str,
        document_tokens: int = 2000,
        language: "LanguageType | None" = None,
    ) -> OutputTokenBudget:
        from core.brevio.enums.language import LanguageType
        from core.shared.utils.adaptive_salience_policy import AdaptiveSaliencePolicy

        if language is None:
            raise ValueError(
                "language is required for output token budget resolution "
                "(model-bound policy texts must match the selected summary language)"
            )
        policy = AdaptiveSaliencePolicy()
        decision = policy.budget(model, summary_level, document_tokens, language)

        format_boost = self.format_multiplier.get(output_format, 1.0)
        style_boost = 1.30 if style.lower() == "diagram" else 1.0

        expected = int(decision.output_target_tokens * format_boost * style_boost)
        minimum = int(decision.output_min_tokens * format_boost)
        maximum = min(
            decision.output_hard_limit,
            int(decision.output_max_tokens * format_boost * style_boost),
        )

        return OutputTokenBudget(
            minimum=minimum,
            expected=expected,
            maximum=maximum,
        )
