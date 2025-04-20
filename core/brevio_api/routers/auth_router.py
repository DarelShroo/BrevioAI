from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from core.brevio_api.dependencies.auth_service_dependency import get_auth_service
from core.brevio_api.models.auth.auth import (
    LoginUser,
    RecoveryPassword,
    RecoveryPasswordOtp,
    RegisterUser,
    UserIdentity,
)
from core.brevio_api.models.responses.auth_response import (
    LoginDataResponse,
    LoginResponse,
    PasswordRecoveryDataResponse,
    PasswordRecoveryResponse,
    RegisterDataResponse,
    RegisterResponse,
)
from core.brevio_api.services.auth_service import AuthService


class AuthRoutes:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/auth", tags=["authentication"])
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.post(
            "/login",
            status_code=status.HTTP_200_OK,
            response_model=LoginDataResponse,
            description="Authenticate a user and return an access token",
            responses={
                401: {"description": "Invalid credentials"},
                422: {"description": "Validation error"},
            },
        )
        async def login(
            login_user: LoginUser,
            auth_service: AuthService = Depends(get_auth_service),
        ) -> JSONResponse:
            login_data: LoginResponse = auth_service.login(login_user)

            response: LoginDataResponse = LoginDataResponse(
                status="success",
                data=login_data,
            )

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=response.model_dump(),
            )

        @self.router.post(
            "/register",
            response_model=RegisterDataResponse,
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
        ) -> JSONResponse:
            register_data: RegisterResponse = await auth_service.register(register_user)

            response = RegisterDataResponse(
                status="success",
                data=register_data,
            )

            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content=response.model_dump(),
            )

        @self.router.post(
            "/password-recovery-handshake",
            response_model=PasswordRecoveryDataResponse,
            status_code=status.HTTP_200_OK,
            description="Initiate password recovery process by sending OTP",
            responses={
                404: {"description": "User not found"},
                422: {"description": "Validation error"},
            },
        )
        async def password_send_otp_recovery(
            identity: RecoveryPassword,
            auth_service: AuthService = Depends(get_auth_service),
        ) -> PasswordRecoveryDataResponse:
            try:
                recovery_password: RecoveryPassword = RecoveryPassword.model_validate(
                    identity
                )

                password_recovery_response: PasswordRecoveryResponse = (
                    await auth_service.password_recovery_handshake(recovery_password)
                )

                response: PasswordRecoveryDataResponse = PasswordRecoveryDataResponse(
                    status="success",
                    data=password_recovery_response,
                )

                return response
            except ValidationError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid user data",
                )

        @self.router.post(
            "/password-recovery-verify",
            response_model=PasswordRecoveryDataResponse,
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
        ) -> PasswordRecoveryDataResponse:
            recovery_password_response: PasswordRecoveryResponse = (
                await auth_service.change_password(recovery_password_otp)
            )
            response: PasswordRecoveryDataResponse = PasswordRecoveryDataResponse(
                status="success",
                data=recovery_password_response,
            )
            return response


auth_router = AuthRoutes().router
