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
from jwt import ExpiredSignatureError, PyJWTError
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import Response

from core.brevio.services.transcription.errors import TranscriptionError
from core.brevio_api.config.dotenv import cors_allow_origins
from core.brevio_api.core.database import AsyncDB
from core.brevio_api.handlers.exception_handlers import (
    auth_service_exception_handler,
    expired_signature_exception_handler,
    global_exception_handler,
    http_exception_handler,
    invalid_file_extension_exception_handler,
    jwt_error_exception_handler,
    provider_error_exception_handler,
    request_validation_exception_handler,
    transcription_error_exception_handler,
    value_error_exception_handler,
)
from core.brevio_api.models.errors.auth_service_exception import AuthServiceException
from core.brevio_api.models.errors.invalid_file_extension import InvalidFileExtension
from core.brevio_api.models.errors.provider_errors import ProviderError
from core.brevio_api.routers import (
    auth_router,
    brevio_router,
    events_router,
    examples_router,
    plans_router,
    user_credential_router,
    user_router,
)
from core.brevio_api.utils.security_runtime import (
    SecurityHeadersMiddleware,
    assert_secure_runtime_config,
    docs_urls_for_environment,
)
from core.shared.utils.environment import is_production_environment

load_dotenv()


def custom_jsonable_encoder(obj: Any) -> Any:
    if isinstance(obj, ObjectId):
        return str(obj)
    return jsonable_encoder(obj)


ExceptionHandler = Callable[[Request, Exception], Union[Response, Awaitable[Response]]]

db = AsyncDB()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    assert_secure_runtime_config()
    await db.verify_connection()
    try:
        from urllib.parse import urlparse

        from core.brevio_api.services.billing.credit_service import CreditService
        from core.brevio_api.services.billing.product_limit_service import (
            ProductLimitService,
        )
        from core.brevio_api.services.billing.usage_service import UsageBillingService
        from core.brevio_api.repositories.billing.usage_repositories import (
            CostRecordRepository,
            UsageRecordRepository,
            usage_billing_collections,
        )

        uri = os.getenv("MONGODB_URI", "")
        path = urlparse(uri).path or "/brevio"
        db_name = path.lstrip("/").split("?")[0] or "brevio"
        database = db.database(db_name)
        await CreditService.from_db(database).ensure_indexes()
        await ProductLimitService.from_db(database).ensure_indexes()
        ucols = usage_billing_collections(database)
        usage = UsageBillingService(
            UsageRecordRepository(ucols["usage"]),
            CostRecordRepository(ucols["costs"]),
        )
        await usage.ensure_indexes()
    except Exception:
        logging.getLogger(__name__).exception("event=billing_indexes_startup_failed")
    yield
    await db.close()


_docs_url, _redoc_url, _openapi_url = docs_urls_for_environment()

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
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
    json_encoder=custom_jsonable_encoder,
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-KEY", "Last-Event-ID"],
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
app.add_exception_handler(ProviderError, provider_error_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(TranscriptionError, transcription_error_exception_handler)  # type: ignore[arg-type]

from core.brevio_api.routers.stripe_router import router as stripe_router

app.include_router(auth_router)
app.include_router(brevio_router)
app.include_router(events_router)
app.include_router(examples_router)
app.include_router(plans_router)
app.include_router(user_router)
app.include_router(user_credential_router)
app.include_router(stripe_router)


def setup_logging() -> None:
    default_level = "INFO" if is_production_environment() else "DEBUG"
    log_level = os.getenv("LOG_LEVEL", default_level).upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        handlers=[logging.StreamHandler()],
    )


setup_logging()
