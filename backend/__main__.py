from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from backend.handlers.exception_handlers import request_validation_exception_handler, pydantic_validation_exception_handler
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

app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)

app.include_router(auth_router)
app.include_router(brevio_router)
app.include_router(user_router)
