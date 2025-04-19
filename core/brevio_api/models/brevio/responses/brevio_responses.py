from typing import Dict, List

from pydantic import BaseModel

from core.brevio.enums.language import LanguageType
from core.brevio.models.category_style import Style
from core.brevio_api.models.responses.base_response import BaseResponse


class LanguagesResponse(BaseModel):
    languages: List[LanguageType]


class LanguagesDataResponse(BaseResponse):
    data: LanguagesResponse


class ModelsResponse(BaseModel):
    models: List[str]


class ModelsDataResponse(BaseResponse):
    data: ModelsResponse


class CategoryStyles(BaseModel):
    advanced_content_combinations: Dict[str, List[Style]]


class CategoryStylesDataResponse(BaseResponse):
    data: CategoryStyles


class CountMediaResponse(BaseModel):
    count: int


class CountMediaDataResponse(BaseResponse):
    data: CountMediaResponse


class CountMediaTimeResponse(BaseModel):
    time: int


class CountMediaTimeDataResponse(BaseResponse):
    data: CountMediaTimeResponse


class ProcessingMessageData(BaseModel):
    message: str = "La generación de resúmenes se está procesando en segundo plano."


class ProcessingMessageResponse(BaseResponse):
    data: ProcessingMessageData
