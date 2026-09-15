from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request

from core.brevio_api.config.dotenv import oauth2_scheme
from core.brevio_api.services.auth_cookies import ACCESS_COOKIE_NAME
from core.brevio_api.services.token_service import TokenService

from .token_dependency import get_token_service


def get_current_user(
    request: Request,
    bearer: Annotated[Optional[str], Depends(oauth2_scheme)],
    token_service: TokenService = Depends(get_token_service),
) -> str:
    token = request.cookies.get(ACCESS_COOKIE_NAME) or bearer
    if not token or token == "null":
        raise HTTPException(status_code=401, detail="Token no proporcionado o nulo")

    payload = token_service.validate_access_token(token)
    user_id = payload.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    return str(user_id)
