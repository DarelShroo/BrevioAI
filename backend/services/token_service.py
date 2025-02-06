from datetime import datetime, timedelta, timezone
import jwt
from fastapi import HTTPException

class TokenService:
    def __init__(self):
        self.secret_key = "8f3e5d1c7a2b9f4e3d1c6a8e7f5b9d3c2a1e0f7d6b8c4a3f9e7d5c1b2a6e8f3d1"
        self.algorithm = "HS256"

    def create_access_token(self, data: dict, expires_delta: timedelta | None = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            # 75 minutos de expiración
            expire = datetime.now(timezone.utc) + timedelta(minutes=75)
        to_encode.update({"exp": int(expire.timestamp())})
        encoded_jwt = jwt.encode(
            to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def validate_access_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self.secret_key,
                                 algorithms=[self.algorithm])

            if int(datetime.now(timezone.utc).timestamp()) > payload["exp"]:
                raise HTTPException(status_code=401, detail="Token expirado")

            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expirado")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Token inválido")

    def refresh_token(self, refresh_token: str) -> str:
        try:
            payload = jwt.decode(
                refresh_token, self.secret_key, algorithms=[self.algorithm])

            new_payload = payload.copy()
            new_payload["exp"] = int(datetime.now(
                timezone.utc).timestamp()) + 3600

            new_token = jwt.encode(
                new_payload, self.secret_key, algorithm=self.algorithm)
            return new_token
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=401, detail="Refresh token inválido")
