# Stdlib imports
from typing import Any, Dict, List, Union

# Third-party imports
from bson import ObjectId
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

# Local imports
from backend.brevio.models.response_model import FolderResponse
from backend.dependencies.auth_service_dependency import get_auth_service
from backend.models.auth.auth import (
    LoginUser,
    RecoveryPassword,
    RecoveryPasswordOtp,
    RegisterUser,
    UserIdentity,
)
from backend.services.auth_service import AuthService
from models.responses.auth_response import (
    LoginResponse,
    PasswordRecoveryResponse,
    RegisterResponse,
)
from models.user.folder_entry import FolderEntry
from models.user.folder_entry_ref import FolderEntryRef


class AuthRoutes:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/auth", tags=["authentication"])
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.post(
            "/login",
            status_code=status.HTTP_200_OK,
            response_model=LoginResponse,
            description="Authenticate a user and return an access token",
            responses={
                401: {"description": "Invalid credentials"},
                422: {"description": "Validation error"},
            },
        )
        def login(
            login_user: LoginUser,
            auth_service: AuthService = Depends(get_auth_service),
        ) -> LoginResponse:
            return auth_service.login(login_user)

        @self.router.post(
            "/register",
            response_model=RegisterResponse,
            status_code=status.HTTP_201_CREATED,
            description="Register a new user account",
            responses={
                400: {"description": "User already exists"},
                422: {"description": "Validation error"},
            },
        )
        async def register(
            register_user: RegisterUser,
            auth_service: AuthService = Depends(get_auth_service),
        ) -> RegisterResponse:
            return await auth_service.register(register_user)

        @self.router.post(
            "/password-recovery-handshake",
            response_model=PasswordRecoveryResponse,
            status_code=status.HTTP_200_OK,
            description="Initiate password recovery process by sending OTP",
            responses={
                404: {"description": "User not found"},
                422: {"description": "Validation error"},
            },
        )
        async def password_send_otp_recovery(
            identity: UserIdentity,
            auth_service: AuthService = Depends(get_auth_service),
        ) -> Dict[str, str]:
            recovery_password = RecoveryPassword(**identity.model_dump())
            return await auth_service.password_recovery_handshake(recovery_password)

        @self.router.post(
            "/password-recovery-verify",
            response_model=PasswordRecoveryResponse,
            status_code=status.HTTP_200_OK,
            description="Verify OTP and complete password recovery",
            responses={
                400: {"description": "Invalid OTP"},
                404: {"description": "User not found"},
                422: {"description": "Validation error"},
            },
        )
        async def password_recovery_verify(
            recovery_password_otp: RecoveryPasswordOtp,
            auth_service: AuthService = Depends(get_auth_service),
        ) -> Dict[str, str]:
            return await auth_service.change_password(recovery_password_otp)


auth_router = AuthRoutes().router
