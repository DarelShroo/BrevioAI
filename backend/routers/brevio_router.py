from typing import Dict, List

from bson import ObjectId
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Request,
    UploadFile,
    status,
)
from pydantic import BaseModel

from backend.brevio.enums.language import LanguageType, parse_language_type
from backend.brevio.enums.model import ModelType
from backend.brevio.enums.output_format_type import OutputFormatType
from models.brevio.brevio_generate import BrevioGenerate
from models.brevio.responses.brevio_responses import (
    LanguagesResponse,
    ModelsResponse,
    ProcessingResponse,
)

from ..brevio.enums import ExtensionType, SourceType
from ..brevio.models import PromptConfig
from ..dependencies import get_current_user, verify_api_key
from ..dependencies.brevio_service_dependency import get_brevio_service
from ..models.brevio.url_yt import UrlYT
from ..services.brevio_service import BrevioService
from ..utils.extension_validator import validate_file_extension


class BrevioRoutes:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/brevio", tags=["brevio"])
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.get(
            "/languages",
            response_model=LanguagesResponse,
            description="Get a list of supported languages for processing",
            status_code=status.HTTP_200_OK,
            responses={401: {"description": "Invalid API key"}},
        )
        async def get_languages(
            verify_api_key: str = Depends(verify_api_key),
            brevio_service: BrevioService = Depends(get_brevio_service),
        ) -> dict:
            return {"languages": brevio_service.get_languages()}

        @self.router.get(
            "/models",
            response_model=ModelsResponse,
            description="Get a list of available AI models",
            status_code=status.HTTP_200_OK,
            responses={401: {"description": "Invalid API key"}},
        )
        async def get_models(
            verify_api_key: str = Depends(verify_api_key),
            brevio_service: BrevioService = Depends(get_brevio_service),
        ) -> dict:
            return {"models": brevio_service.get_models()}

        @self.router.get(
            "/categories-styles",
            # response_model=CategoryStylesResponse,
            description="Get available categories and their associated styles",
            status_code=status.HTTP_200_OK,
            responses={401: {"description": "Invalid API key"}},
        )
        async def get_categories_styles(
            verify_api_key: str = Depends(verify_api_key),
            brevio_service: BrevioService = Depends(get_brevio_service),
        ) -> dict:
            return {
                "categories_styles": brevio_service.get_all_category_style_combinations()
            }

        @self.router.post(
            "/count-yt-videos",
            response_model=int,
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
        ) -> int:
            result = await brevio_service.count_media_in_yt_playlist(request.url)
            return int(result)

        @self.router.post(
            "/count-time-yt-video",
            response_model=int,
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
        ) -> int:
            duration_data = await brevio_service.get_total_duration(request.url)
            return await brevio_service.get_total_duration(request.url)

        @self.router.post(
            "/summary-media",
            response_model=ProcessingResponse,
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
        ) -> dict:
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
            response_model=ProcessingResponse,
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
        ) -> dict:
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
        ) -> dict:
            files_data = [
                (file.filename or "unknown", await file.read())
                for file in files
                if validate_file_extension(file, allowed_extensions)
            ]

            prompt_config = PromptConfig(
                model=model.value,
                category=category,
                style=style,
                format=format.value,
                language=language.name,
                source_types=source_types.value,
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

            return {
                "message": "La generación de resúmenes se está procesando en segundo plano."
            }

        @self.router.post("/summary-yt-playlist")
        async def generate_summary_yt_playlist(
            brevio_generate: BrevioGenerate,
            background_tasks: BackgroundTasks = BackgroundTasks(),
            brevio_service: BrevioService = Depends(get_brevio_service),
            _current_user: ObjectId = Depends(get_current_user),
        ):
            background_tasks.add_task(
                brevio_service.generate, brevio_generate, _current_user
            )
            return {
                "message": "La generación de resúmenes se está procesando en segundo plano."
            }


brevio_router = BrevioRoutes().router
