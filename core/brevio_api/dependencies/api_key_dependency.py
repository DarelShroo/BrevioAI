from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

from core.brevio_api.config.dotenv import API_KEY

api_key_header = APIKeyHeader(name="X-API-KEY")


def verify_api_key(api_key: str = Depends(api_key_header)) -> str:
    if api_key != API_KEY:
        raise HTTPException(
            status_code=403, detail="Acceso prohibido: API Key inválida"
        )
    return api_key
