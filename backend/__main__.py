from fastapi import FastAPI, HTTPException
from backend.handlers.exception_handlers import global_exception_handler, http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
import logging
from .routers import auth_router, brevio_router, user_router
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

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

app.include_router(auth_router)
app.include_router(brevio_router)
app.include_router(user_router)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
