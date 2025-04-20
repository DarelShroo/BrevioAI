import jwt
from bson import ObjectId
from fastapi import Depends, HTTPException

from core.brevio_api.config.config import oauth2_scheme
from core.brevio_api.services.token_service import TokenService

from .token_dependency import get_token_service


def get_current_user(
    token: str = Depends(oauth2_scheme),
    token_service: TokenService = Depends(get_token_service),
) -> ObjectId:
    if not token or token == "null":
        raise HTTPException(status_code=401, detail="Token no proporcionado o nulo")

    try:
        payload = token_service.validate_access_token(token)
        if payload is None:
            raise HTTPException(status_code=401, detail="Token inválido o expirado")
        user_id = ObjectId(payload["id"])
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.DecodeError:
        raise HTTPException(status_code=401, detail="Token inválido")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado al validar el token: {str(e)}",
        )
