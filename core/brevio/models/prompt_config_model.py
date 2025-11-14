from enum import Enum
from typing import TYPE_CHECKING, Any, Type

from pydantic import field_serializer, field_validator

from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.models.base_model import BaseModel
from core.shared.enums.model import ModelType


class PromptConfig(BaseModel):
    model: ModelType
    category: str
    style: str
    format: OutputFormatType
    language: LanguageType
    summary_level: SummaryLevel

    @field_validator("category", "style")
    @classmethod
    def validate_category_and_style(cls, value: Any, info: Any) -> Any:
        from ..services.advanced_content_generator import AdvancedPromptGenerator

        if value is None:
            return value

        acg = AdvancedPromptGenerator()
        available_templates = acg.get_available_templates()

        if info.field_name == "category":
            if value not in available_templates:
                raise ValueError(f"Categoría inválida: {value}")

        if info.field_name == "style":
            category = info.data.get("category")
            if category:
                styles_for_category = set(available_templates.get(category, {}).keys())
                if value not in styles_for_category:
                    raise ValueError(
                        f"Estilo '{value}' inválido para categoría '{category}'"
                    )
        return value

    @field_validator("model", mode="before")
    @classmethod
    def convert_model_enum(cls, value: Any, info: Any) -> Any:
        field_info = cls.model_fields.get(info.field_name)

        if field_info is None or field_info.annotation is None:
            raise ValueError(f"Invalid field: {info.field_name}")

        enum_type: Type[Enum] = field_info.annotation

        if not issubclass(enum_type, Enum):
            raise ValueError(f"Field {info.field_name} is not an Enum type")

        if isinstance(value, str):
            for member in enum_type:
                if member.value == value:
                    return member
            raise ValueError(f"Invalid {info.field_name}: {value}")

        return value

    @field_validator("language", mode="before")
    @classmethod
    def convert_language_enum(cls, value: Any, info: Any) -> Any:
        field_info = cls.model_fields.get(info.field_name)

        if field_info is None or field_info.annotation is None:
            raise ValueError(f"Invalid field: {info.field_name}")

        enum_type: Type[Enum] = field_info.annotation

        if not issubclass(enum_type, Enum):
            raise ValueError(f"Field {info.field_name} is not an Enum type")

        if isinstance(value, str):
            for member in enum_type:
                if member.name == value.upper():
                    return member
            raise ValueError(f"Invalid {info.field_name}: {value}")

        return value

    @field_serializer("model")
    @classmethod
    def serialize_model(cls, value: ModelType) -> str:
        return value.value

    @field_serializer("language")
    @classmethod
    def serialize_language(cls, value: LanguageType) -> str:
        return value.name

    @field_serializer("format")
    @classmethod
    def serialize_format(cls, value: OutputFormatType) -> str:
        return value.value

    @field_serializer("summary_level")
    @classmethod
    def serialize_summary_level(cls, value: SummaryLevel) -> str:
        return value.value
