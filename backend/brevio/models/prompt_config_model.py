# En prompt_config_model.py
from pydantic import BaseModel, field_validator, Field
from backend.brevio.enums.language import LanguageType
from backend.brevio.enums.output_format_type import OutputFormatType
from backend.brevio.enums.source_type import SourceType
from backend.brevio.services.advanced_content_generator import AdvancedContentGenerator

class PromptConfig(BaseModel):
    category: str 
    style: str
    format: OutputFormatType
    language: LanguageType
    source: SourceType = SourceType.PDF

    @field_validator('category', 'style')
    @classmethod
    def validate_category_and_style(cls, value, info):
        if value is None:
            return value
        
        acg = AdvancedContentGenerator()
        combinations = acg.get_all_category_style_combinations()
        
        if info.field_name == 'category' and value not in {c[0] for c in combinations}:
            raise ValueError(f"Categoría inválida: {value}")
        
        if info.field_name == 'style':
            category = info.data.get('category')
            if category and not any(c[0] == category and c[1] == value for c in combinations):
                raise ValueError(f"Estilo '{value}' inválido para categoría '{category}'")
        
        return value

    @field_validator('language', mode='before')
    def convert_enum(cls, value):
        if isinstance(value, str):
            return LanguageType[value.upper()]
        return value