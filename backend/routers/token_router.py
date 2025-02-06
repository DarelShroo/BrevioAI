from fastapi import APIRouter, Depends
from ..services.token_service import TokenService
from ..dependencies.token_dependency import get_token_service
from ..models.token import Token

class TokenRouter:
    def __init__(self):
        self.router = APIRouter(
            prefix="/token",
            tags=["token"]
        )
        self._register_routes()

    def _register_routes(self):
        @self.router.post("/expire")
        def expire_token(token: Token, token_service: TokenService = Depends(get_token_service)):
            try:
                return token_service.expire_token(token)
            except Exception as e:
                return e


token_router = TokenRouter().router
