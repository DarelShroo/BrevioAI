from typing import Any, Dict, List, Literal, Optional

from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette import status

from core.brevio.enums.language import LanguageType
from core.brevio.models.category_style import Style
from core.brevio_api.models.responses.base_response import BaseResponse


class LanguagesResponse(BaseModel):
    languages: Any


class LanguagesDataResponse(BaseResponse):
    data: LanguagesResponse


class ModelCatalogItem(BaseModel):
    id: str
    provider: str
    access: Literal["local", "pay_per_use"]
    requires_api_key: bool
    display_name: str
    output_token_param: Optional[str] = None
    parameters: List[str] = Field(default_factory=list)
    reasoning: Optional[str] = None
    reasoning_values: List[str] = Field(default_factory=list)
    status: Optional[str] = None
    retirement: Optional[str] = None
    recommended: Optional[bool] = None


class ProviderCatalogItem(BaseModel):
    id: str
    access: Literal["local", "pay_per_use"]
    requires_api_key: bool


class ModelsResponse(BaseModel):
    models: List[str]
    catalog: List[ModelCatalogItem] = Field(default_factory=list)
    providers: List[ProviderCatalogItem] = Field(default_factory=list)
    environment: Optional[str] = None


class ModelsDataResponse(BaseResponse):
    data: ModelsResponse


class CategoryStyles(BaseModel):
    advanced_content_combinations: Dict[str, List[Style]]


class CategoryStylesDataResponse(BaseResponse):
    data: Any


class SummaryLevelDataResponse(BaseResponse):
    data: Any


class OutputFormatDataResponse(BaseResponse):
    data: Any


class CountMediaResponse(BaseModel):
    count: int


class CountMediaDataResponse(BaseResponse):
    data: CountMediaResponse


class CountMediaTimeResponse(BaseModel):
    time: int


class CountMediaTimeDataResponse(BaseResponse):
    data: CountMediaTimeResponse


class TranscriptionProviderItem(BaseModel):
    id: str
    implemented: bool
    user_access: bool
    requires_api_key: bool
    access: Literal["local", "pay_per_use"]
    display_name: str


class TranscriptionModelItem(BaseModel):
    id: str
    provider: str
    vendor_model_id: Optional[str] = None
    status: str
    recommended: bool
    retirement: Optional[str] = None
    parameters: List[str] = Field(default_factory=list)
    display_name: str
    requires_api_key: bool
    user_access: bool


class TranscriptionProvidersResponse(BaseModel):
    environment: str
    providers: List[TranscriptionProviderItem] = Field(default_factory=list)
    models: List[TranscriptionModelItem] = Field(default_factory=list)
    selectable: List[str] = Field(default_factory=list)
    default: Optional[str] = None
    default_model: Optional[str] = None


class TranscriptionProvidersDataResponse(BaseResponse):
    data: TranscriptionProvidersResponse


class ProcessingMessageData(BaseModel):
    message: str = "La generación de resúmenes se está procesando en segundo plano."


class ProcessingMessageResponse(BaseResponse):
    data: ProcessingMessageData
    task_id: str | None = None
    folder_entry_id: str | None = None
