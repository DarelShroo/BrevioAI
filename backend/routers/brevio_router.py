from typing import List
from fastapi import APIRouter, Depends, BackgroundTasks, File, Form, UploadFile
from pydantic import ValidationError
from backend.models.brevio.brevio_generate import BrevioGenerate, BrevioGenerateContent
from backend.models.brevio.url_yt import UrlYT
from backend.services.brevio_service import BrevioService
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

        @self.router.post("/count-yt-videos")
        async def count_media_in_yt_playlist(request: UrlYT, verify_api_key: str = Depends(verify_api_key)):
            return await self._brevio_service.count_media_in_yt_playlist(request.url)

        @self.router.post("/count-time-yt-video")
        async def get_media_duration(request: UrlYT, verify_api_key: str = Depends(verify_api_key)):
            return await self._brevio_service.get_media_duration(request.url)

        @self.router.post("/summary-yt-playlist")
        async def generate_summary_yt_playlist(brevio_generate_list: BrevioGenerate, background_tasks: BackgroundTasks, name: str = "", _current_user: str = Depends(get_current_user)):
            background_tasks.add_task(
                self._brevio_service.generate, brevio_generate_list, _current_user, name)
            return {"message": "La generación de resúmenes se está procesando en segundo plano."}
        
        @self.router.post("/summary-media")
        async def generate_summary_media(
            background_tasks: BackgroundTasks,
            language: str = Form(...),
            model: str = Form(...),
            content: str = Form(...),
            files: List[UploadFile] = File(...),
            _current_user: str = Depends(get_current_user)
        ):
            files_data = []
            for file in files:
                file_content = await file.read()
                files_data.append((file.filename, file_content))
            
            brevio_generate_content = BrevioGenerateContent(language=language, model=model, content=content)
            
            background_tasks.add_task(
                self._brevio_service.generate_summary_media_upload,
                files_data,
                _current_user,
                brevio_generate_content
            )
            
            return {"message": "La generación de resúmenes se está procesando en segundo plano."}
        
        @self.router.post("/summary-pdf")
        async def generate_summary_pdf(
            background_tasks: BackgroundTasks,
            language: str = Form(...),
            model: str = Form(...),
            content: str = Form(...),
            files: List[UploadFile] = File(...),
            _current_user: str = Depends(get_current_user)
            ):
            
            files_data = [(file.filename, await file.read()) for file in files]

            brevio_generate_content = BrevioGenerateContent(language=language, model=model, content=content)

            background_tasks.add_task(
                self._brevio_service.generate_summary_pdf,
                files_data,
                _current_user,
                brevio_generate_content
            )

            return {"message": "La generación de resúmenes se está procesando en segundo plano."}
            
        @self.router.post("/summary-docx")
        async def generate_summary_docx(
            background_tasks: BackgroundTasks,
            language: str = Form(...),
            model: str = Form(...),
            content: str = Form(...),
            files: List[UploadFile] = File(...),
            _current_user: str = Depends(get_current_user)
        ):
            files_data = [(file.filename, await file.read()) for file in files]

            brevio_generate_content = BrevioGenerateContent(language=language, model=model, content=content)

            background_tasks.add_task(
                self._brevio_service.generate_summary_docx,
                files_data,
                _current_user,
                brevio_generate_content
            )

            return {"message": "La generación de resúmenes se está procesando en segundo plano."}



        
brevio_router = BrevioRoutes().router
