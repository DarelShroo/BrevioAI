from fastapi import Depends

from ..services.token_service import TokenService


def get_token_service() -> TokenService:
    return TokenService()
