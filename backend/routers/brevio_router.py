from typing import List
from fastapi import APIRouter, Body, Depends, BackgroundTasks, File, Form, UploadFile
from backend.brevio.enums.extension import ExtensionType
from backend.brevio.enums.source_type import SourceType
from backend.brevio.models.prompt_config_model import PromptConfig
from backend.brevio.models.summary_config_model import SummaryConfig
from backend.models.brevio.brevio_generate import BrevioGenerate
from backend.models.brevio.url_yt import UrlYT
from backend.services.brevio_service import BrevioService
from ..utils.extension_validator import validate_file_extension
from ..dependencies.api_key_dependency import verify_api_key
from ..dependencies.user_dependency import get_current_user


class BrevioRoutes:
    def __init__(self):
        self.router = APIRouter(
            prefix="/brevio",
            tags=["brevio"]
        )
        self._register_routes()
        self._brevio_service = BrevioService()

    def _register_routes(self):
        @self.router.get("/languages")
        async def get_languages(verify_api_key: str = Depends(verify_api_key)):
            return {"languages": await self._brevio_service.get_languages()}

        @self.router.get("/models")
        async def get_models(verify_api_key: str = Depends(verify_api_key)):
            return {"models": await self._brevio_service.get_models()}

        @self.router.get("/categories-styles")
        async def get_models(verify_api_key: str = Depends(verify_api_key)):
            return {"catogories_styles": await self._brevio_service.get_all_category_style_combinations()}

        @self.router.post("/count-yt-videos")
        async def count_media_in_yt_playlist(request: UrlYT, verify_api_key: str = Depends(verify_api_key)):
            return await self._brevio_service.count_media_in_yt_playlist(request.url)

        @self.router.post("/count-time-yt-video")
        async def get_media_duration(request: UrlYT, verify_api_key: str = Depends(verify_api_key)):
            return await self._brevio_service.get_media_duration(request.url)

        @self.router.post("/summary-yt-playlist")
        async def generate_summary_yt_playlist(
            brevio_generate: BrevioGenerate,
            background_tasks: BackgroundTasks = BackgroundTasks(),
            _current_user: str = Depends(get_current_user)
        ):
            background_tasks.add_task(
                self._brevio_service.generate, brevio_generate, _current_user)
            return {"message": "La generación de resúmenes se está procesando en segundo plano."}

        @self.router.post("/summary-media")
        async def generate_summary_media(
            files: List[UploadFile] = File(...),
            language: str = Form(...),
            model: str = Form(...),
            category: str = Form(...),
            style: str = Form(...),
            format: str = Form(...),
            background_tasks: BackgroundTasks = BackgroundTasks(),
            _current_user: str = Depends(get_current_user)
        ):
            allowed_extensions = [
                ExtensionType.MP3.value]

            files_data = [
                (file.filename, await file.read()) for file in files if validate_file_extension(file, allowed_extensions)
            ]

            summary_config = SummaryConfig(
                model=model, category=category, style=style)
            prompt_config = PromptConfig(
                category=category, style=style, format=format, language=language, source=SourceType.PDF.value)

            background_tasks.add_task(
                self._brevio_service.generate_summary_media_upload,
                files_data,
                _current_user,
                summary_config,
                prompt_config
            )

            return {"message": "La generación de resúmenes se está procesando en segundo plano."}

        @self.router.post("/summary-documents")
        async def generate_summary_documents(
            files: List[UploadFile] = File(...),
            language: str = Form(...),
            model: str = Form(...),
            category: str = Form(...),
            style: str = Form(...),
            format: str = Form(...),
            background_tasks: BackgroundTasks = BackgroundTasks(),
            _current_user: str = Depends(get_current_user)
        ):
            allowed_extensions = [
                ExtensionType.DOCX.value, ExtensionType.PDF.value]

            files_data = [
                (file.filename, await file.read()) for file in files if validate_file_extension(file, allowed_extensions)
            ]

            summary_config = SummaryConfig(
                model=model, category=category, style=style)
            prompt_config = PromptConfig(
                category=category, style=style, format=format, language=language, source=SourceType.PDF.value)

            background_tasks.add_task(
                self._brevio_service.generate_summary_documents,
                files_data,
                _current_user,
                summary_config,
                prompt_config
            )

            return {"message": "La generación de resúmenes se está procesando en segundo plano."}


brevio_router = BrevioRoutes().router
