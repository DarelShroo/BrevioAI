from fastapi import APIRouter

from backend.brevio.models.response_model import LanguageResponse, ModelResponse
from backend.models.brevio.url_yt import UrlYT
from backend.brevio import __main__ as Brevio
class BrevioRoutes:
    def __init__(self):
        self.router = APIRouter(
            prefix="/brevio",
            tags=["brevio"]
        )
        self._register_routes()
    def _register_routes(self):
        @self.router.get("/languages")
        async def languages():
            return {"languages": LanguageResponse().get_languages()}
        
        @self.router.get("/models")
        async def models():
            return {"models": ModelResponse().get_models()}
        
        @self.router.post("/count-yt-videos")
        async def count_videos_in_yt_playlist(request: UrlYT):
            return Brevio.YTService.count_videos_in_yt_playlist(request.url)

        @self.router.post("/count-time-yt-video")
        async def get_video_duration(request: UrlYT):
            return { Brevio.YTService.get_videos_duration(request.url)}



brevio_router = BrevioRoutes().router