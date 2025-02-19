import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from backend.models.brevio.brevio_generate import BrevioGenerate
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
            return {"languages": self._brevio_service.get_languages()}

        @self.router.get("/models")
        async def get_models(verify_api_key: str = Depends(verify_api_key)):
            return {"models": self._brevio_service.get_models()}

        @self.router.post("/count-yt-videos")
        async def count_media_in_yt_playlist(request: UrlYT, verify_api_key: str = Depends(verify_api_key)):
            return await self._brevio_service.count_media_in_yt_playlist(request.url)

        @self.router.post("/count-time-yt-video")
        async def get_media_duration(request: UrlYT, verify_api_key: str = Depends(verify_api_key)):
            return await self._brevio_service.get_media_duration(request.url)

        @self.router.post("/generate-summary-yt-playlist")
        async def generate_summary_yt_playlist(brevio_generate_list: BrevioGenerate, background_tasks: BackgroundTasks, name: str = "", _current_user: str = Depends(get_current_user)):
            background_tasks.add_task(
                self._brevio_service.generate, brevio_generate_list, _current_user, name)
            return {"message": "La generación de resúmenes se está procesando en segundo plano."}
        
        @self.router.post("/generate-summary-media")
        async def generate_summary_media(
            files: List[UploadFile] = File(...),
            _current_user: str = Depends(get_current_user)
        ):
            return await self._brevio_service.generate_summary_media(files, _current_user)


brevio_router = BrevioRoutes().router
