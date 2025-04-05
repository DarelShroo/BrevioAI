import os

from dotenv import load_dotenv
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer

load_dotenv()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

api_key_header = APIKeyHeader(name="X-API-KEY")

API_KEY = os.getenv("API_KEY", "DEFAULT_SECRET_KEY")
SECRET_KEY = os.getenv("SECRET_TOKEN_KEY", "default_secret_key")
ALGORITHM = os.getenv("TOKEN_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
