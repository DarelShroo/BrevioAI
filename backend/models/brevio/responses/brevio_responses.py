from typing import Dict, List

from brevio.models.base_model import BaseModel


class LanguagesResponse(BaseModel):
    languages: List[str]


class ModelsResponse(BaseModel):
    models: List[str]


class CategoryStylesResponse(BaseModel):
    categories_styles: Dict[str, List[str]]


class ProcessingResponse(BaseModel):
    message: str
