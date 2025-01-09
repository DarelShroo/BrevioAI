from fastapi import FastAPI
import uvicorn
from brevio_service import __main__ as BrevioMain
import logging
import sys
import os
from pydantic import BaseModel

app = FastAPI()

logging.basicConfig(level=logging.INFO) 
logger = logging.getLogger(__name__)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'brevio_service')))

class UrlRequest(BaseModel):
    url: str
    language: str

@app.post("/brevio")
async def brevio(request: UrlRequest):
    logger.info(f"Accediendo al endpoint con URL: {request.url} y language: {request.language}")
    return BrevioMain.main([request.url])

@app.get("/whisper/languages")
async def languages(request: UrlRequest):
    return BrevioMain.main([request.url])
