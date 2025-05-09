from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from fastapi import HTTPException, status

from core.brevio_api.config.dotenv import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    SECRET_KEY,
)


class TokenService:
    def __init__(self) -> None:
        self.__expire_minutes = ACCESS_TOKEN_EXPIRE_MINUTES
        self.__secret_key = SECRET_KEY
        self.__algorithm = ALGORITHM

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
        return self.__create_token(data, expires_delta)

    def validate_access_token(self, token: str) -> Dict[Any, Any]:
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
