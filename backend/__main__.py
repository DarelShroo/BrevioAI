from fastapi import FastAPI

from .models.brevio import BrevioYT
from .brevio import __main__ as Brevio
from .brevio.models.response_model import LanguageResponse
from .brevio.models.response_model import ModelResponse
import sys
import os
from fastapi.middleware.cors import CORSMiddleware
from .routers.auth_router import auth_router
from .routers.brevio_router import brevio_router
from .routers.user_router import user_router

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
app.include_router(brevio_router)
app.include_router(user_router)

sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), 'brevio')))

@app.post("/brevio")
async def brevio(request: BrevioYT):
    return Brevio.main([request.url])


