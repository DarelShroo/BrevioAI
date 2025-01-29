from fastapi import FastAPI

from .models.brevio import BrevioYT, Login, UrlYT
from .brevio import __main__ as Brevio
from .brevio.models.response_model import LanguageResponse
from .brevio.models.response_model import ModelResponse
import sys
import os
from fastapi.middleware.cors import CORSMiddleware
from .routers.auth_route import Auth  # Ajusta el path según la definición real

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), 'brevio')))
    
@app.post("/brevio")
async def brevio(request: BrevioYT):
    return Brevio.main([request.url])
    
@app.get("/languages")
async def languages():
    return LanguageResponse().__str__()

@app.post("/count-yt-videos")
async def count_videos_in_yt_playlist(request: UrlYT):
    return Brevio.YTService.count_videos_in_yt_playlist(request.url)

@app.post("/count-time-yt-video")
async def get_video_duration(request: UrlYT):
    return { Brevio.YTService.get_videos_duration(request.url)}

@app.post("/login")
async def login(request: Login):
    return Auth.login(request.identity, request.password)

@app.post("/register")
async def login(request: Login):
    return Auth.login(request.identity, request.password)

@app.get("/models")
async def models():
    return ModelResponse().__str__()
