import base64
from typing import Dict, List, Optional, Tuple, cast

from bson import ObjectId
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from pydantic import HttpUrl

from core.brevio.enums.extension import ExtensionType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio_api.celery import celery_app
from core.brevio_api.dependencies.api_key_dependency import verify_api_key
from core.brevio_api.dependencies.brevio_service_dependency import get_brevio_service
from core.brevio_api.dependencies.usage_cost_tracker_dependency import (
    get_cost_token_tracker,
)
from core.brevio_api.dependencies.user_dependency import get_current_user
from core.brevio_api.models.brevio.responses.brevio_responses import (
    CategoryStyles,
    CategoryStylesDataResponse,
    CountMediaDataResponse,
    CountMediaResponse,
    CountMediaTimeDataResponse,
    CountMediaTimeResponse,
    LanguagesDataResponse,
    LanguagesResponse,
    ModelsDataResponse,
    ModelsResponse,
    OutputFormatDataResponse,
    ProcessingMessageData,
    ProcessingMessageResponse,
    SummaryLevelDataResponse,
)
from core.brevio_api.models.brevio.url_yt import UrlYT
from core.brevio_api.services.billing.usage_cost_tracker import UsageCostTracker
from core.brevio_api.services.brevio_service import BrevioService
from core.brevio_api.tasks import generate_summary_task, process_summary_task
from core.brevio_api.utils.language_utils import language_from_form
from core.shared.enums.model import ModelType
from core.shared.models.brevio.brevio_generate import BrevioGenerate


class BrevioRoutes:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/brevio", tags=["brevio"])
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.get(
            "/languages",
            response_model=LanguagesDataResponse,
            description="Get a list of supported languages for processing",
            status_code=status.HTTP_200_OK,
            responses={401: {"description": "Invalid API key"}},
        )
        async def get_languages(
            verify_api_key: str = Depends(verify_api_key),
            brevio_service: BrevioService = Depends(get_brevio_service),
        ) -> LanguagesDataResponse:
            languages = brevio_service.get_languages()
            response = LanguagesDataResponse(
                data=LanguagesResponse(languages=languages),
            )
            return response

        @self.router.get(
            "/models",
            response_model=ModelsDataResponse,
            description="Get a list of available AI models",
            status_code=status.HTTP_200_OK,
            responses={401: {"description": "Invalid API key"}},
        )
        async def get_models(
            verify_api_key: str = Depends(verify_api_key),
            brevio_service: BrevioService = Depends(get_brevio_service),
        ) -> ModelsDataResponse:
            models = brevio_service.get_models()
            response = ModelsDataResponse(
                data=ModelsResponse(models=models),
            )
            return response

        @self.router.get(
            "/categories-styles",
            response_model=CategoryStylesDataResponse,
            description="Get available categories and their associated styles",
            status_code=status.HTTP_200_OK,
            responses={401: {"description": "Invalid API key"}},
        )
        async def get_categories_styles(
            verify_api_key: str = Depends(verify_api_key),
            brevio_service: BrevioService = Depends(get_brevio_service),
        ) -> CategoryStylesDataResponse:
            all_categories_styles = (
                await brevio_service.get_all_category_style_combinations()
            )
            categories_styles = CategoryStyles(
                advanced_content_combinations=all_categories_styles
            )
            response = CategoryStylesDataResponse(data=categories_styles)
            return response

        @self.router.get(
            "/output-formats",
            response_model=OutputFormatDataResponse,
            description="Get available output formats",
            status_code=status.HTTP_200_OK,
            responses={401: {"description": "Invalid API key"}},
        )
        async def get_formats(
            verify_api_key: str = Depends(verify_api_key),
            brevio_service: BrevioService = Depends(get_brevio_service),
        ) -> OutputFormatDataResponse:
            formats = brevio_service.get_all_formats()
            response = OutputFormatDataResponse(data=formats)
            return response

        @self.router.get(
            "/summary-levels",
            response_model=SummaryLevelDataResponse,
            description="Get available summary levels",
            status_code=status.HTTP_200_OK,
            responses={401: {"description": "Invalid API key"}},
        )
        async def get_summary_levels(
            verify_api_key: str = Depends(verify_api_key),
            brevio_service: BrevioService = Depends(get_brevio_service),
        ) -> SummaryLevelDataResponse:
            summary_levels = brevio_service.get_all_summary_levels()
            response = SummaryLevelDataResponse(data=summary_levels)
            return response

        @self.router.post(
            "/count-yt-videos",
            response_model=CountMediaDataResponse,
            description="Count the number of videos in a YouTube playlist",
            status_code=status.HTTP_200_OK,
            responses={
                401: {"description": "Invalid API key"},
                422: {"description": "Invalid URL format"},
            },
        )
        async def count_media_in_yt_playlist(
            request: UrlYT,
            verify_api_key: str = Depends(verify_api_key),
            brevio_service: BrevioService = Depends(get_brevio_service),
        ) -> CountMediaDataResponse:
            result = await brevio_service.count_media_in_yt_playlist(
                HttpUrl(request.url)
            )
            if not isinstance(result, int):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Invalid response format from brevio service",
                )
            response = CountMediaDataResponse(
                data=CountMediaResponse(count=result),
            )
            return response

        @self.router.post(
            "/count-time-yt-video",
            response_model=CountMediaTimeDataResponse,
            description="Get the total duration of a YouTube video in seconds",
            status_code=status.HTTP_200_OK,
            responses={
                401: {"description": "Invalid API key"},
                422: {"description": "Invalid URL format"},
            },
        )
        async def get_total_duration(
            request: UrlYT,
            verify_api_key: str = Depends(verify_api_key),
            brevio_service: BrevioService = Depends(get_brevio_service),
        ) -> CountMediaTimeDataResponse:
            try:
                duration_data = await brevio_service.get_total_duration(request.url)
                if not isinstance(duration_data, int):
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Invalid response format from brevio service",
                    )
                return CountMediaTimeDataResponse(
                    data=CountMediaTimeResponse(time=duration_data),
                )
            except ValueError as ve:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve)
                )
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="An unexpected error occurred",
                )

        @self.router.post(
            "/summary-media",
            response_model=ProcessingMessageResponse,
            description="""
                Generate summaries from media files (MP3).
                The process runs in the background and results will be available asynchronously.
            """,
            status_code=status.HTTP_202_ACCEPTED,
            responses={
                401: {"description": "Unauthorized"},
                415: {"description": "Unsupported media type"},
                422: {"description": "Validation error"},
            },
        )
        async def generate_summary_media(
            files: List[UploadFile] = File(...),
            language: LanguageType = Depends(language_from_form),
            model: ModelType = Form(...),
            category: str = Form(...),
            style: str = Form(...),
            format: OutputFormatType = Form(...),
            summary_level: SummaryLevel = Form(...),
            _current_user: ObjectId = Depends(get_current_user),
            brevio_service: BrevioService = Depends(get_brevio_service),
        ) -> JSONResponse:
            # Define valid extensions for media files
            valid_media_extensions = [ExtensionType.MP3.value]

            # Validate each uploaded file
            for uploaded_file in files:
                if uploaded_file.filename:
                    file_extension = uploaded_file.filename.split(".")[-1].lower()
                    if file_extension not in [
                        ext.lower() for ext in valid_media_extensions
                    ]:
                        raise HTTPException(
                            status_code=415,
                            detail=f"File type not allowed: {uploaded_file.filename}",
                        )
                else:
                    raise HTTPException(
                        status_code=415,
                        detail="File must have a valid filename with extension",
                    )

            # Convert files to data for Celery task
            file_data_list = [
                (file.filename or "unknown", await file.read()) for file in files
            ]

            # Start Celery task
            task = process_summary_task.delay(
                files=file_data_list,
                language=language.value,
                model=model.value,
                category=category,
                style=style,
                format=format.value,
                summary_level=summary_level.value,
                _current_user=str(_current_user),
                is_media=True,
            )  # type: ignore

            # Return response
            response = ProcessingMessageResponse(data=ProcessingMessageData())
            return JSONResponse(
                content={"task_id": task.id, **response.model_dump()},
                status_code=status.HTTP_202_ACCEPTED,
            )

        @self.router.post(
            "/summary-documents",
            response_model=ProcessingMessageResponse,
            description="""
                Generate summaries from document files (PDF, DOCX).
                The process runs in the background and results will be available asynchronously.
            """,
            status_code=status.HTTP_202_ACCEPTED,
            responses={
                401: {"description": "Unauthorized"},
                415: {"description": "Unsupported media type"},
                422: {"description": "Validation error"},
            },
        )
        async def generate_summary_documents(
            files: List[UploadFile] = File(...),
            language: LanguageType = Depends(language_from_form),
            model: ModelType = Form(...),
            category: str = Form(...),
            style: str = Form(...),
            format: OutputFormatType = Form(...),
            summary_level: SummaryLevel = Form(...),
            _current_user: ObjectId = Depends(get_current_user),
        ) -> JSONResponse:
            # Define valid extensions for document files
            valid_document_extensions = [
                ExtensionType.DOCX.value,
                ExtensionType.PDF.value,
            ]

            # Validate each uploaded file
            for uploaded_file in files:
                if uploaded_file.filename:
                    file_extension = uploaded_file.filename.split(".")[-1].lower()
                    if file_extension not in [
                        ext.lower() for ext in valid_document_extensions
                    ]:
                        raise HTTPException(
                            status_code=415,
                            detail=f"File type not allowed: {uploaded_file.filename}",
                        )
                else:
                    raise HTTPException(
                        status_code=415,
                        detail="File must have a valid filename with extension",
                    )

            # Convert files to data for Celery task
            file_data_list = [
                (file.filename or "unknown", await file.read()) for file in files
            ]

            # Start Celery task
            task = process_summary_task.delay(
                files=file_data_list,
                language=language.value,
                model=model.value,
                category=category,
                style=style,
                format=format.value,
                summary_level=summary_level.value,
                _current_user=str(_current_user),
                is_media=False,
            )  # type: ignore

            # Return response
            response = ProcessingMessageResponse(data=ProcessingMessageData())
            return JSONResponse(
                content={"task_id": task.id, **response.model_dump()},
                status_code=status.HTTP_202_ACCEPTED,
            )

        @self.router.post("/summary-yt-playlist")
        async def generate_summary_yt_playlist(
            brevio_generate: BrevioGenerate,
            _current_user: ObjectId = Depends(get_current_user),
        ) -> JSONResponse:
            print(brevio_generate.model_dump(mode="json"))
            generate_summary_task.delay(
                brevio_generate.model_dump(mode="json"), str(_current_user)
            )  # type: ignore

            response = ProcessingMessageResponse(data=ProcessingMessageData())
            return JSONResponse(
                content=response.model_dump(), status_code=status.HTTP_202_ACCEPTED
            )


brevio_router = BrevioRoutes().router
