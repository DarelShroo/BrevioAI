from fastapi import APIRouter, Depends, BackgroundTasks
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
            durations = self._brevio_service.get_media_duration(request.url)
            return durations
        @self.router.post("/generate")
        async def generate_summaries(brevio_generate_list: BrevioGenerate, background_tasks: BackgroundTasks, name: str = "", _current_user: str = Depends(get_current_user)):
            background_tasks.add_task(self._brevio_service.generate, brevio_generate_list, _current_user, name)
            return {"message": "La generación de resúmenes se está procesando en segundo plano."}

brevio_router = BrevioRoutes().router
