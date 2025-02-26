from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    errors = []
    for err in exc.errors():
        errors.append({
            "field": err["loc"][-1],
            "error": err["type"],
            "message": err["msg"],
            "input": err.get("ctx", {}).get("input", None)
        })
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "message": "Se han encontrado errores de validación.",
            "errors": errors,
            "signature": {
                "brand": "Brevio",
                "version": "v1.0",
                "contact": "support@brevio.com"
            }
        }
    )

from fastapi.exceptions import RequestValidationError

async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        errors.append({
            "field": err["loc"][-1],
            "error": err["type"],
            "message": err["msg"],
            "input": err.get("ctx", {}).get("input", None)
        })
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "message": "Se han encontrado errores de validación.",
            "errors": errors,
            "signature": {
                "brand": "Brevio",
                "version": "v1.0",
                "contact": "support@brevio.com"
            }
        }
    )
