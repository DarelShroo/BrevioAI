import logging
from typing import Awaitable, Callable, Union

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from jwt import ExpiredSignatureError, PyJWTError
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import Response

from handlers.exception_handlers import (
    auth_service_exception_handler,
    expired_signature_exception_handler,
    global_exception_handler,
    http_exception_handler,
    invalid_file_extension_exception_handler,
    jwt_error_exception_handler,
    pydantic_validation_exception_handler,
    request_validation_exception_handler,
    value_error_exception_handler,
)
from models.errors.auth_service_exception import AuthServiceException
from models.errors.invalid_file_extension import InvalidFileExtension

from .routers import auth_router, brevio_router, user_router

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
)

load_dotenv()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ExceptionHandler = Callable[[Request, Exception], Union[Response, Awaitable[Response]]]

app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
app.add_exception_handler(
    InvalidFileExtension, invalid_file_extension_exception_handler
)
app.add_exception_handler(ExpiredSignatureError, expired_signature_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(ValueError, value_error_exception_handler)
app.add_exception_handler(AuthServiceException, auth_service_exception_handler)
app.add_exception_handler(PyJWTError, jwt_error_exception_handler)

app.include_router(auth_router)
app.include_router(brevio_router)
app.include_router(user_router)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
