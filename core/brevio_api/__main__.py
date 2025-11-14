import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Awaitable, Callable, Union

from bson import ObjectId
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jwt import ExpiredSignatureError, PyJWTError
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import Response

from core.brevio_api.core.database import AsyncDB
from core.brevio_api.handlers.exception_handlers import (
    auth_service_exception_handler,
    expired_signature_exception_handler,
    global_exception_handler,
    http_exception_handler,
    invalid_file_extension_exception_handler,
    jwt_error_exception_handler,
    request_validation_exception_handler,
    value_error_exception_handler,
)
from core.brevio_api.models.errors.auth_service_exception import AuthServiceException
from core.brevio_api.models.errors.invalid_file_extension import InvalidFileExtension
from core.brevio_api.routers import (
    auth_router,
    billing_router,
    brevio_router,
    user_router,
)

load_dotenv()


def custom_jsonable_encoder(obj: Any) -> Any:
    if isinstance(obj, ObjectId):
        return str(obj)
    return jsonable_encoder(obj)


ExceptionHandler = Callable[[Request, Exception], Union[Response, Awaitable[Response]]]

db = AsyncDB()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Código de startup
    await db.verify_connection()
    yield
    # Código de shutdown (si hace falta cerrar conexión)
    await db.close()


app = FastAPI(
    title="Brevio API",
    description="""
    Brevio API provides a robust backend service for managing authentication, 
    user operations, and core business functionality.
    
    Key Features:
    * Authentication and Authorization
    * User Management
    * Custom Brevio Operations
    """,
    version="1.0.0",
    contact={
        "name": "Brevio Development Team",
        "url": "https://github.com/BrevioAI",
    },
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    json_encoder=custom_jsonable_encoder,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de manejadores de excepciones
app.add_exception_handler(ValidationError, request_validation_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(InvalidFileExtension, invalid_file_extension_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(ExpiredSignatureError, expired_signature_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, global_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(ValueError, value_error_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(AuthServiceException, auth_service_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(PyJWTError, jwt_error_exception_handler)  # type: ignore[arg-type]

app.include_router(auth_router)
app.include_router(brevio_router)
app.include_router(user_router)
app.include_router(billing_router)


def setup_logging() -> None:
    log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()  # Cambia por INFO en producción
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        handlers=[logging.StreamHandler()],
    )


setup_logging()
