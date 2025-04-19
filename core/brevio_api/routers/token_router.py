from fastapi import APIRouter


class TokenRouter:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/token", tags=["token"])
        self._register_routes()

    def _register_routes(self) -> None:
        pass


token_router = TokenRouter().router
