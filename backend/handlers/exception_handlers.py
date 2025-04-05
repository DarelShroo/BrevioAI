from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jwt.exceptions import ExpiredSignatureError, PyJWTError
from pydantic import ValidationError

from backend.models.errors.invalid_file_extension import InvalidFileExtension
from models.errors.auth_service_exception import AuthServiceException


async def pydantic_validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    errors = []
    for err in exc.errors():
        errors.append(
            {
                "field": err["loc"][-1],
                "error": err["type"],
                "message": err["msg"],
                "input": err.get("ctx", {}).get("input", None),
            }
        )
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "message": "Se han encontrado errores de validación.",
            "errors": errors,
            "signature": {
                "brand": "Brevio",
                "version": "v1.0",
                "contact": "support@brevio.com",
            },
        },
    )


async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = []
    for err in exc.errors():
        errors.append(
            {
                "field": err["loc"][-1],
                "error": err["type"],
                "message": err["msg"],
                "input": err.get("ctx", {}).get("input", None),
            }
        )
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "message": "Se han encontrado errores de validación.",
            "errors": errors,
            "signature": {
                "brand": "Brevio",
                "version": "v1.0",
                "contact": "support@brevio.com",
            },
        },
    )


async def invalid_file_extension_exception_handler(
    request: Request, exc: InvalidFileExtension
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "errors": [
                {
                    "field": "file",
                    "error": "Invalid file extension",
                    "message": f"The file '{exc.filename}' has an invalid extension.",
                    "allowed_extensions": exc.allowed_extensions,
                }
            ],
            "signature": {
                "brand": "Brevio",
                "version": "v1.0",
                "contact": "support@brevio.com",
            },
        },
    )


async def expired_signature_exception_handler(
    request: Request, exc: ExpiredSignatureError
) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "status": "error",
            "message": "Token de autenticación expirado.",
            "signature": {
                "brand": "Brevio",
                "version": "v1.0",
                "contact": "support@brevio.com",
            },
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "signature": {
                "brand": "Brevio",
                "version": "v1.0",
                "contact": "support@brevio.com",
            },
        },
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    print(f"Error interno: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Ocurrió un error inesperado. Por favor, inténtelo más tarde.",
            "signature": {
                "brand": "Brevio",
                "version": "v1.0",
                "contact": "support@brevio.com",
            },
        },
    )


async def value_error_exception_handler(
    request: Request, exc: ValueError
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "status": "error",
            "message": f"Valor inválido en alguno de los campos. Por favor, revisa los datos proporcionados.",
            "signature": {
                "brand": "Brevio",
                "version": "v1.0",
                "contact": "support@brevio.com",
            },
        },
    )


async def auth_service_exception_handler(
    request: Request, exc: AuthServiceException
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "status": "error",
            "message": f"Error en el servicio de autenticación: {str(exc)}",
            "signature": {
                "brand": "Brevio",
                "version": "v1.0",
                "contact": "support@brevio.com",
            },
        },
    )


async def jwt_error_exception_handler(
    request: Request, exc: PyJWTError
) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "status": "error",
            "message": "Token de autenticación no válido.",
            "signature": {
                "brand": "Brevio",
                "version": "v1.0",
                "contact": "support@brevio.com",
            },
        },
    )
