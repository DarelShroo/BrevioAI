import os
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from dotenv import load_dotenv

load_dotenv()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

api_key_header = APIKeyHeader(name="X-API-KEY")

API_KEY = os.getenv("API_KEY", "DEFAULT_SECRET_KEY")
