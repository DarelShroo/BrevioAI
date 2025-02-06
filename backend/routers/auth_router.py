from fastapi import APIRouter, Depends
from ..models.user.login_user import LoginUser
from ..models.user.register_user import RegisterUser
from ..services.auth_service import AuthService
from ..dependencies.auth_service_dependency import get_auth_service

class AuthRoutes:
    def __init__(self):
        self.router = APIRouter(
            prefix="/auth",
            tags=["authentication"]
        )
        self._register_routes()

    def _register_routes(self):
        @self.router.post("/login")
        async def login(
            login_user: LoginUser,
            auth_service: AuthService = Depends(get_auth_service)
        ):
            return await auth_service.login(login_user)

        @self.router.post("/register")
        async def register(
            register_user: RegisterUser,
            auth_service: AuthService = Depends(get_auth_service)
        ):
            return await auth_service.register(register_user)


auth_router = AuthRoutes().router
