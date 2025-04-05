from fastapi import APIRouter


class UserRouter:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/user", tags=["user"])
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.post("/")
        async def get_user_profile() -> None:
            pass


user_router = UserRouter().router
