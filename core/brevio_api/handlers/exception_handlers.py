from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jwt.exceptions import ExpiredSignatureError, PyJWTError
from pydantic import ValidationError

from core.brevio_api.models.errors.auth_service_exception import AuthServiceException
from core.brevio_api.models.errors.invalid_file_extension import InvalidFileExtension
from core.brevio_api.models.responses.signature_response import SignatureResponse

SIGNATURE = SignatureResponse()


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
            "signature": SIGNATURE.model_dump(),
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
            "signature": SIGNATURE.model_dump(),
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
            "signature": SIGNATURE.model_dump(),
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
            "signature": SIGNATURE.model_dump(),
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "signature": SIGNATURE.model_dump(),
        },
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    print(f"Error interno: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Ocurrió un error inesperado. Por favor, inténtelo más tarde.",
            "signature": SIGNATURE.model_dump(),
        },
    )


async def value_error_exception_handler(
    request: Request, exc: ValueError
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "status": "error",
            "message": "Valor inválido en alguno de los campos. Por favor, revisa los datos proporcionados.",
            "signature": SIGNATURE.model_dump(),
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
            "signature": SIGNATURE.model_dump(),
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
            "signature": SIGNATURE.model_dump(),
        },
    )
