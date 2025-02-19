from fastapi import APIRouter, Depends, HTTPException

from backend.models.user.recovery_password_otp import RecoveryPasswordOtp
from ..models.user.login_user import LoginUser
from ..models.user.register_user import RegisterUser
from ..services.auth_service import AuthService
from ..dependencies.auth_service_dependency import get_auth_service
from ..models.user.user_identity import UserIdentity
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
            try:
                response = await auth_service.register(register_user)
                return response
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Internal Server Error")
            
        @self.router.post('/password-recovery-handshake')
        async def password_send_otp_recovery(
            identity: UserIdentity,
            auth_service: AuthService = Depends(get_auth_service)
        ):
            return await auth_service.password_recovery_handshake(identity)

        @self.router.post('/password-recovery-verify')
        async def password_recovery_verify(
            recovery_password_otp: RecoveryPasswordOtp,
            auth_service: AuthService = Depends(get_auth_service)
        ):
            
            return await auth_service.change_password(recovery_password_otp)
        
        @self.router.post('/prueba')
        async def prueba(
            auth_service: AuthService = Depends(get_auth_service),
        ):
            
            return True


auth_router = AuthRoutes().router
