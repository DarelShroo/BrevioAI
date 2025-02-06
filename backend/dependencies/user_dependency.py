from fastapi import HTTPException, Depends
import jwt
from backend.services.token_service import TokenService
from .token_dependency import get_token_service
from ..config.config import oauth2_scheme

def get_current_user(token: str = Depends(oauth2_scheme), token_service: TokenService = Depends(get_token_service)):
    try:
        payload = token_service.validate_access_token(token)

        if payload is None:
            raise HTTPException(
                status_code=401,
                detail="Token inválido o expirado",
            )

        return payload["id"]

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.DecodeError:
        raise HTTPException(status_code=401, detail="Token inválido")
