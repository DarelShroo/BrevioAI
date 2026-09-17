from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jwt.exceptions import ExpiredSignatureError, PyJWTError
from pydantic import ValidationError

from core.brevio.services.transcription.errors import TranscriptionError
from core.brevio_api.models.errors.auth_service_exception import AuthServiceException
from core.brevio_api.models.errors.invalid_file_extension import InvalidFileExtension
from core.brevio_api.models.errors.provider_errors import (
    ProviderError,
    ProviderErrorKind,
)
from core.brevio_api.models.responses.signature_response import SignatureResponse

SIGNATURE = SignatureResponse()


async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = []
    for err in exc.errors():
        errors.append(
            {
                "field": err["loc"][-1],
                "error": err["type"],
                "message": (
                    err["msg"].split(",", 1)[1] if "," in err["msg"] else err["msg"]
                ),
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
    content = {
        "status": "error",
        "message": exc.detail,
        "code": getattr(exc, "code", None) or "FILE_FORMAT_NOT_ALLOWED",
        "errors": [
            {
                "field": "file",
                "error": "Invalid file extension",
                "message": f"The file '{exc.filename}' has an invalid extension.",
                "allowed_extensions": exc.allowed_extensions,
            }
        ],
        "signature": SIGNATURE.model_dump(),
    }
    return JSONResponse(status_code=exc.status_code, content=content)


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
    content = {
        "status": "error",
        "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
        "signature": SIGNATURE.model_dump(),
    }
    code = getattr(exc, "code", None)
    if code:
        content["code"] = code
    headers = getattr(exc, "headers", None) or {}
    return JSONResponse(
        status_code=exc.status_code, content=content, headers=dict(headers)
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


async def transcription_error_exception_handler(
    request: Request, exc: TranscriptionError
) -> JSONResponse:
    status_code = 400
    if exc.code == "TRANSCRIPTION_PROVIDER_NOT_ALLOWED":
        status_code = 403
    elif exc.code in {
        "TRANSCRIPTION_API_KEY_REQUIRED",
        "TRANSCRIPTION_API_KEY_INVALID",
    }:
        status_code = 401
    elif exc.code in {
        "TRANSCRIPTION_OPENAI_TIMEOUT",
        "TRANSCRIPTION_TIMEOUT",
        "MEDIA_FFMPEG_TIMEOUT",
    }:
        status_code = 504
    elif exc.code == "TRANSCRIPTION_QUOTA_EXCEEDED":
        status_code = 429
    elif exc.code in {
        "TRANSCRIPTION_OPENAI_ERROR",
        "TRANSCRIPTION_LOCAL_WHISPER_ERROR",
    }:
        status_code = 502
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "code": exc.code,
            "message": exc.code,
            "signature": SIGNATURE.model_dump(),
        },
    )


async def provider_error_exception_handler(
    request: Request, exc: ProviderError
) -> JSONResponse:
    code = exc.kind.value if isinstance(exc.kind, ProviderErrorKind) else str(exc.kind)

    if exc.kind == ProviderErrorKind.USER_CREDENTIAL_REQUIRED:
        status_code = 401
        message = "Esta solicitud requiere una credencial de API en tu perfil o créditos de pago por uso."
    elif exc.kind == ProviderErrorKind.PLATFORM_CREDENTIAL_UNAVAILABLE:
        status_code = 503
        message = (
            "El servicio no está disponible temporalmente para procesar esta solicitud."
        )
    elif exc.kind == ProviderErrorKind.CREDENTIAL_UNAVAILABLE:
        status_code = 400
        message = "No hay una credencial disponible para procesar la solicitud."
    elif exc.kind in (
        ProviderErrorKind.UNAUTHORIZED,
        ProviderErrorKind.INVALID_CREDENTIAL,
    ):
        status_code = 401
        message = "Credencial de API no válida o rechazada."
    elif exc.kind == ProviderErrorKind.INSUFFICIENT_FUNDS:
        status_code = 402
        message = "Cuota o fondos insuficientes en la cuenta del proveedor."
    elif exc.kind == ProviderErrorKind.INSUFFICIENT_CREDITS:
        status_code = 402
        message = (
            getattr(exc, "message", None)
            or "Créditos insuficientes para procesar esta solicitud."
        )
    elif exc.kind == ProviderErrorKind.MODEL_NOT_ALLOWED:
        status_code = 403
        message = "Este modelo no está disponible en el entorno actual."
    elif exc.kind == ProviderErrorKind.RATE_LIMIT_EXCEEDED:
        status_code = 429
        message = "Límite de peticiones alcanzado. Inténtelo más tarde."
    elif exc.kind == ProviderErrorKind.PROVIDER_ERROR:
        status_code = 502
        message = "Error de comunicación con el proveedor del servicio."
    else:
        status_code = 500
        message = "Error en la gestión de credenciales."

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "code": code,
            "message": message,
            "signature": SIGNATURE.model_dump(),
        },
    )
