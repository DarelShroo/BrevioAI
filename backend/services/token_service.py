from datetime import datetime, timedelta, timezone
import jwt
from os import getenv
from fastapi import HTTPException, status

class TokenService:
    __secret_key: str
    __algorithm: str
    __expire_minutes: int

    def __init__(self):
        self.__secret_key = getenv("SECRET_TOKEN_KEY")
        self.__algorithm = getenv("TOKEN_ALGORITHM")
        self.__expire_minutes = int(getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))

        if not self.__secret_key or not self.__algorithm:
            raise ValueError("Faltan configuraciones del token en variables de entorno")

    def __create_token(self, data: dict, expires_delta: timedelta | None = None) -> str:
        try:
            to_encode = data.copy()
            expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=self.__expire_minutes))
            to_encode.update({"exp": expire.timestamp()})
            encoded_jwt = jwt.encode(to_encode, self.__secret_key, algorithm=self.__algorithm)
            return encoded_jwt
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error inesperado al crear el token: {str(e)}"
            )

    def create_access_token(self, data: dict, expires_delta: timedelta | None = None) -> str:
        return self.__create_token(data, expires_delta)

    def validate_access_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self.__secret_key, algorithms=[self.__algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expirado"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error inesperado al validar el token: {str(e)}"
            )

    def refresh_token(self, refresh_token: str, expires_delta: timedelta | None = None) -> str:
        try:
            payload = jwt.decode(refresh_token, self.__secret_key, algorithms=[self.__algorithm])
            if 'exp' not in payload:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Refresh token inválido"
                )
            return self.__create_token(payload, expires_delta)
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token inválido"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error inesperado al refrescar el token: {str(e)}"
            )
