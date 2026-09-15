from typing import Any, List, Optional

from fastapi import Depends, Form
from pydantic import BaseModel, model_validator

from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.source_type import SourceType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio.services.advanced_content_generator import AdvancedPromptGenerator
from core.brevio_api.utils.language_utils import language_from_form
from core.shared.enums.model import ModelType


class DocumentProcessingRequest(BaseModel):
    language: LanguageType
    model: ModelType
    category: str
    style: str
    format: OutputFormatType
    summary_level: SummaryLevel
    source_types: Optional[List[SourceType]] = None

    @model_validator(mode="after")
    def validate_source_types_for_style(self) -> "DocumentProcessingRequest":
        if not self.source_types:
            return self

        available_templates = AdvancedPromptGenerator().get_available_templates()
        category_styles = available_templates.get(self.category, {})
        style_info = category_styles.get(self.style)

        if style_info is None:
            return self

        allowed_source_types = {
            source_type.value
            for source_type in style_info.get("source_types", [])
            if hasattr(source_type, "value")
        }

        if not allowed_source_types:
            return self

        invalid_values = [
            source_type.value
            for source_type in self.source_types
            if source_type.value not in allowed_source_types
        ]

        if invalid_values:
            raise ValueError(
                "Invalid source_types for selected category/style: "
                + ", ".join(invalid_values)
            )

        return self

    def to_prompt_config(self) -> PromptConfig:
        return PromptConfig(
            model=self.model,
            category=self.category,
            style=self.style,
            format=self.format,
            language=self.language,
            summary_level=self.summary_level,
        )

    @classmethod
    def from_form(
        cls,
        language: LanguageType = Depends(language_from_form),
        model: ModelType = Form(...),
        category: str = Form(...),
        style: str = Form(...),
        format: OutputFormatType = Form(...),
        summary_level: SummaryLevel = Form(...),
        source_types: Optional[List[SourceType]] = Form(None),
    ) -> "DocumentProcessingRequest":
        return cls(
            language=language,
            model=model,
            category=category,
            style=style,
            format=format,
            summary_level=summary_level,
            source_types=source_types,
        )
