import os

from dotenv import load_dotenv
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer

from core.shared.utils.environment import jwt_algorithm, jwt_secret_key

load_dotenv()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

api_key_header = APIKeyHeader(name="X-API-KEY")

API_KEY = os.getenv("API_KEY", "DEFAULT_SECRET_KEY")
# Snapshots at import. TokenService re-reads JWT secret/algorithm/TTL at construction.
SECRET_KEY = jwt_secret_key()
ALGORITHM = jwt_algorithm()


def cors_allow_origins() -> list[str]:
    raw = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost,http://localhost:80",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
