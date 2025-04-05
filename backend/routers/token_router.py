from fastapi import APIRouter, Depends

from ..dependencies.token_dependency import get_token_service
from ..models.token.token import Token
from ..services.token_service import TokenService


class TokenRouter:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/token", tags=["token"])
        self._register_routes()

    def _register_routes(self) -> None:
        pass


token_router = TokenRouter().router
