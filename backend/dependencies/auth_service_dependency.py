from fastapi import Depends
from pymongo.database import Database
from ..dependencies.db_dependency import get_db
from ..services.token_service import TokenService
from ..dependencies.token_dependency import get_token_service
from ..services.auth_service import AuthService


def get_auth_service(
        db: Database = Depends(get_db),
        token_service: TokenService = Depends(get_token_service)
):
    return AuthService(db, token_service)
