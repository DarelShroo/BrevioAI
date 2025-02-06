from fastapi import APIRouter, Depends
from backend.brevio.models.response_model import LanguageResponse, ModelResponse
from backend.models.brevio.url_yt import UrlYT
from backend.brevio import __main__ as Brevio

from ..dependencies.api_key_dependency import verify_api_key

class BrevioRoutes:
    def __init__(self):
        self.router = APIRouter(
            prefix="/brevio",
            tags=["brevio"]
        )
        self._register_routes()

    def _register_routes(self):
        @self.router.get("/languages")
        async def languages(verify_api_key: str = Depends(verify_api_key)):
            return {"languages": LanguageResponse().get_languages()}

        @self.router.get("/models")
        async def models(verify_api_key: str = Depends(verify_api_key)):
            return {"models": ModelResponse().get_models()}

        @self.router.post("/count-yt-videos")
        async def count_videos_in_yt_playlist(request: UrlYT, verify_api_key: str = Depends(verify_api_key)):
            return Brevio.YTService.count_videos_in_yt_playlist(request.url)

        @self.router.post("/count-time-yt-video")
        async def get_video_duration(request: UrlYT, verify_api_key: str = Depends(verify_api_key)):
            return {Brevio.YTService.get_videos_duration(request.url)}


brevio_router = BrevioRoutes().router
