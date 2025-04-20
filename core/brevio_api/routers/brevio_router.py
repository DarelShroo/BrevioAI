from typing import Dict, List

from bson import ObjectId
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from pydantic import HttpUrl, ValidationError

from core.brevio.enums.extension import ExtensionType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.model import ModelType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.source_type import SourceType
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio_api.dependencies.api_key_dependency import verify_api_key
from core.brevio_api.dependencies.brevio_service_dependency import get_brevio_service
from core.brevio_api.dependencies.user_dependency import get_current_user
from core.brevio_api.models.brevio.brevio_generate import BrevioGenerate
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
    ProcessingMessageData,
    ProcessingMessageResponse,
)
from core.brevio_api.models.brevio.url_yt import UrlYT
from core.brevio_api.services.brevio_service import BrevioService
from core.brevio_api.utils.extension_validator import validate_file_extension
from core.brevio_api.utils.language_utils import parse_language_type


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
            languages: List[str] = brevio_service.get_languages()
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
            all_categories_styles = brevio_service.get_all_category_style_combinations()
            categories_styles = CategoryStyles(
                advanced_content_combinations=all_categories_styles
            )
            response = CategoryStylesDataResponse(data=categories_styles)
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
            except Exception as e:
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
            language: LanguageType = Depends(parse_language_type),
            model: ModelType = Form(...),
            category: str = Form(...),
            style: str = Form(...),
            format: OutputFormatType = Form(...),
            source_types: SourceType = Form(...),
            background_tasks: BackgroundTasks = BackgroundTasks(),
            _current_user: ObjectId = Depends(get_current_user),
            brevio_service: BrevioService = Depends(get_brevio_service),
        ) -> JSONResponse:
            return await process_summary(
                files,
                language,
                model,
                category,
                style,
                format,
                source_types,
                background_tasks,
                _current_user,
                brevio_service,
                [ExtensionType.MP3.value],
                is_media=True,
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
            language: LanguageType = Depends(parse_language_type),
            model: ModelType = Form(...),
            category: str = Form(...),
            style: str = Form(...),
            format: OutputFormatType = Form(...),
            source_types: SourceType = Form(...),
            background_tasks: BackgroundTasks = BackgroundTasks(),
            _current_user: ObjectId = Depends(get_current_user),
            brevio_service: BrevioService = Depends(get_brevio_service),
        ) -> JSONResponse:
            return await process_summary(
                files,
                language,
                model,
                category,
                style,
                format,
                source_types,
                background_tasks,
                _current_user,
                brevio_service,
                [ExtensionType.DOCX.value, ExtensionType.PDF.value],
                is_media=False,
            )

        async def process_summary(
            files: List[UploadFile],
            language: LanguageType,
            model: ModelType,
            category: str,
            style: str,
            format: OutputFormatType,
            source_types: SourceType,
            background_tasks: BackgroundTasks,
            _current_user: ObjectId,
            brevio_service: "BrevioService",
            allowed_extensions: List[str],
            is_media: bool = False,
        ) -> JSONResponse:
            files_data = [
                (file.filename or "unknown", await file.read())
                for file in files
                if validate_file_extension(file, allowed_extensions)
            ]

            prompt_config = PromptConfig(
                model=model,
                category=category,
                style=style,
                format=format,
                language=language,
                source_types=source_types,
            )

            service_method = (
                brevio_service.generate_summary_media_upload
                if is_media
                else brevio_service.generate_summary_documents
            )

            background_tasks.add_task(
                service_method,
                files_data,
                _current_user,
                prompt_config,
            )

            response = ProcessingMessageResponse(data=ProcessingMessageData())

            return JSONResponse(
                content=response.model_dump(), status_code=status.HTTP_202_ACCEPTED
            )

        @self.router.post("/summary-yt-playlist")
        async def generate_summary_yt_playlist(
            brevio_generate: BrevioGenerate,
            background_tasks: BackgroundTasks = BackgroundTasks(),
            brevio_service: BrevioService = Depends(get_brevio_service),
            _current_user: ObjectId = Depends(get_current_user),
        ) -> JSONResponse:
            print(_current_user)
            background_tasks.add_task(
                brevio_service.generate, brevio_generate, _current_user
            )

            response = ProcessingMessageResponse(data=ProcessingMessageData())

            return JSONResponse(
                content=response.model_dump(), status_code=status.HTTP_202_ACCEPTED
            )


brevio_router = BrevioRoutes().router
