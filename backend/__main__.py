from fastapi import FastAPI

from .models.brevio import BrevioYT, LoginUser, UrlYT
from .brevio import __main__ as Brevio
from .brevio.models.response_model import LanguageResponse
from .brevio.models.response_model import ModelResponse
import sys
import os
from fastapi.middleware.cors import CORSMiddleware
from .routers.auth_routes import auth_router
from dotenv import load_dotenv
app = FastAPI()

load_dotenv()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), 'brevio')))

@app.post("/brevio")
async def brevio(request: BrevioYT):
    return Brevio.main([request.url])
    
@app.get("/brevio/languages")
async def languages():
    return LanguageResponse().__str__()

@app.post("/brevio/count-yt-videos")
async def count_videos_in_yt_playlist(request: UrlYT):
    return Brevio.YTService.count_videos_in_yt_playlist(request.url)

@app.post("/brevio/count-time-yt-video")
async def get_video_duration(request: UrlYT):
    return { Brevio.YTService.get_videos_duration(request.url)}

@app.get("/brevio/models")
async def models():
    return ModelResponse().__str__()
