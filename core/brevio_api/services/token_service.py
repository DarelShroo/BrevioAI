from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4

import jwt
from fastapi import HTTPException, status

from core.shared.utils.environment import (
    access_token_expire_minutes,
    jwt_algorithm,
    jwt_secret_key,
    refresh_token_expire_days,
)

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


class TokenService:
    def __init__(self) -> None:
        self.__expire_minutes = access_token_expire_minutes()
        self.__refresh_days = refresh_token_expire_days()
        self.__secret_key = jwt_secret_key()
        self.__algorithm = jwt_algorithm()

    @property
    def access_max_age_seconds(self) -> int:
        return self.__expire_minutes * 60

    @property
    def refresh_max_age_seconds(self) -> int:
        return self.__refresh_days * 24 * 60 * 60

    def __create_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        try:
            to_encode = data.copy()
            expire = datetime.now(timezone.utc) + (
                expires_delta or timedelta(minutes=self.__expire_minutes)
            )
            to_encode.update({"exp": expire.timestamp()})
            encoded_jwt = jwt.encode(
                to_encode, self.__secret_key, algorithm=self.__algorithm
            )
            return encoded_jwt
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error inesperado al crear el token: {str(e)}",
            )

    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        payload = {
            **data,
            "typ": TOKEN_TYPE_ACCESS,
            "jti": uuid4().hex,
        }
        delta = expires_delta or timedelta(minutes=self.__expire_minutes)
        return self.__create_token(payload, delta)

    def create_refresh_token(self, user_id: str, family_id: str) -> Tuple[str, str]:
        jti = uuid4().hex
        payload = {
            "id": user_id,
            "typ": TOKEN_TYPE_REFRESH,
            "fam": family_id,
            "jti": jti,
        }
        token = self.__create_token(payload, timedelta(days=self.__refresh_days))
        return token, jti

    def _decode(self, token: str) -> Dict[Any, Any]:
        try:
            payload = jwt.decode(
                token, self.__secret_key, algorithms=[self.__algorithm]
            )
            if not isinstance(payload, dict):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="El payload no es un diccionario válido",
                )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error inesperado al validar el token: {str(e)}",
            )

    def validate_access_token(self, token: str) -> Dict[Any, Any]:
        payload = self._decode(token)
        if payload.get("typ") != TOKEN_TYPE_ACCESS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
            )
        if not payload.get("id"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
            )
        return payload

    def validate_refresh_token(self, token: str) -> Dict[Any, Any]:
        payload = self._decode(token)
        if payload.get("typ") != TOKEN_TYPE_REFRESH:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
            )
        if not payload.get("id") or not payload.get("jti") or not payload.get("fam"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
            )
        return payload
