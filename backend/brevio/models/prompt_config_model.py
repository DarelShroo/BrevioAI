from pydantic import BaseModel, field_validator, Field
from backend.brevio.enums.model import ModelType
from ..enums import LanguageType, OutputFormatType, SourceType
from ..services.advanced_content_generator import AdvancedContentGenerator

class PromptConfig(BaseModel):
    model: ModelType
    category: str
    style: str
    format: OutputFormatType
    language: LanguageType
    source_types: SourceType

    @field_validator('category', 'style', 'source_types')
    @classmethod
    def validate_category_and_style(cls, value, info):
        if value is None:
            return value

        acg = AdvancedContentGenerator()
        available_templates = acg.get_available_templates()
        
        if info.field_name == 'category':
            if value not in available_templates:
                raise ValueError(f"Categoría inválida: {value}")

        if info.field_name == 'style':
            category = info.data.get('category')
            if category:
                styles_for_category = {
                    style['category'] for style in available_templates.get(category, [])}
                if value not in styles_for_category:
                    raise ValueError(
                        f"Estilo '{value}' inválido para categoría '{category}'")

        if info.field_name == 'source_types':
            category = info.data.get('category')
            style = info.data.get('style')
            if category:
                valid_sources = {
                    source_type for template in available_templates.get(category, [])
                    for source_type in template['source_types'] if template['category'] == style
                }
                if value not in valid_sources:
                    raise ValueError(
                        f"Source '{value}' inválido para categoría '{category}' y estilo '{style}'")

        return value

    @field_validator('model', 'language', mode='before')
    def convert_enum(cls, value, info):
        enum_type = cls.model_fields[info.field_name].annotation
        if isinstance(value, str):
            try:
                return enum_type[value.upper()]
            except KeyError:
                raise ValueError(f"Invalid {info.field_name}: {value}")
        return value
