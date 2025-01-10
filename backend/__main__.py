from fastapi import FastAPI, HTTPException
import uvicorn
from brevio_service import __main__ as BrevioMain
from brevio_service.models.response_model import LanguageResponse
from brevio_service.models.response_model import ModelResponse

import logging
import sys
import os
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), 'brevio_service')))


class UrlRequest(BaseModel):
    url: str
    language: str


@app.post("/brevio")
async def brevio(request: UrlRequest):
    return BrevioMain.main([request.url])
    

@app.get("/languages")
async def languages():
    return LanguageResponse().__str__()


@app.get("/models")
async def models():
    return ModelResponse().__str__()
