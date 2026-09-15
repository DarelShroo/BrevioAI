from dataclasses import dataclass

from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.style import StyleType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.services.advanced_content_generator import AdvancedPromptGenerator
from core.shared.enums.model import ModelType
from core.shared.utils.model_tokens_utils import get_encoder


@dataclass(frozen=True)
class PromptEstimationResult:
    prompt_template_tokens: int
    structural_tokens: int
    prompt_text: str


class PromptEstimationService:
    def __init__(self) -> None:
        self._generator = AdvancedPromptGenerator()

    async def build_prompt(
        self,
        category: str,
        style: str,
        output_format: OutputFormatType,
        language: LanguageType,
        summary_level: SummaryLevel,
    ) -> str:
        return await self._generator.generate_prompt(
            category=CategoryType(category),
            style=StyleType(self._resolve_style_name(category, style)),
            output_format=output_format,
            lang=language,
            summary_level=summary_level,
        )

    def estimate_prompt_tokens(self, prompt: str, model: ModelType) -> int:
        encoder = get_encoder(model)
        return len(encoder.encode(prompt))

    def estimate_structural_tokens(self, prompt: str, model: ModelType) -> int:
        encoder = get_encoder(model)
        structure = self.structural_wrapper_text(prompt)
        return len(encoder.encode(structure))

    def structural_wrapper_text(self, content: str) -> str:
        return f"<document>\n{content}\n</document>"

    def _resolve_style_name(self, category: str, style: str) -> str:
        if category == CategoryType.REQUIREMENTS.value and style == "elicitation":
            return "elicitation"
        return style
