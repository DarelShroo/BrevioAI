from dataclasses import dataclass

from core.shared.utils.model_capabilities import ModelCapabilities
from core.shared.utils.output_token_policy import OutputTokenBudget


@dataclass(frozen=True)
class ContextValidationResult:
    can_process: bool
    reason: str | None
    requires_chunking: bool
    requires_output_reduction: bool
    required_tokens: int


class ContextValidator:
    def validate(
        self,
        input_tokens: int,
        output_budget: OutputTokenBudget,
        capabilities: ModelCapabilities,
    ) -> ContextValidationResult:
        worst_case = input_tokens + output_budget.maximum
        if worst_case <= capabilities.context_window:
            return ContextValidationResult(
                can_process=True,
                reason=None,
                requires_chunking=False,
                requires_output_reduction=False,
                required_tokens=worst_case,
            )

        reduced_output_required = input_tokens + output_budget.minimum
        if reduced_output_required <= capabilities.context_window:
            return ContextValidationResult(
                can_process=True,
                reason="OUTPUT_REDUCTION_REQUIRED",
                requires_chunking=False,
                requires_output_reduction=True,
                required_tokens=reduced_output_required,
            )

        if capabilities.supports_chunking:
            return ContextValidationResult(
                can_process=True,
                reason="MODEL_REQUIRES_CHUNKING",
                requires_chunking=True,
                requires_output_reduction=False,
                required_tokens=worst_case,
            )

        return ContextValidationResult(
            can_process=False,
            reason="MODEL_CONTEXT_EXCEEDED",
            requires_chunking=False,
            requires_output_reduction=False,
            required_tokens=worst_case,
        )
