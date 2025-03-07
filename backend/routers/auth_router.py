from fastapi import APIRouter, Depends
from ..models.auth.auth import LoginUser, RecoveryPasswordOtp, RegisterUser, UserIdentity
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
            auth_service: AuthService = Depends(get_auth_service),
        ):
            return await auth_service.login(login_user)

        @self.router.post("/register")
        async def register(
            register_user: RegisterUser,
            auth_service: AuthService = Depends(get_auth_service),
        ):
            return await auth_service.register(register_user)

        @self.router.post('/password-recovery-handshake')
        async def password_send_otp_recovery(
            identity: UserIdentity,
            auth_service: AuthService = Depends(get_auth_service),
        ):
            return await auth_service.password_recovery_handshake(identity)

        @self.router.post('/password-recovery-verify')
        async def password_recovery_verify(
            recovery_password_otp: RecoveryPasswordOtp,
            auth_service: AuthService = Depends(get_auth_service),
        ):
            return await auth_service.change_password(recovery_password_otp)

auth_router = AuthRoutes().router
