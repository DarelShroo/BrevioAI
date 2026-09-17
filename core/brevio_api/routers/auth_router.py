from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from core.brevio_api.dependencies.auth_service_dependency import get_auth_service
from core.brevio_api.dependencies.token_dependency import get_token_service
from core.brevio_api.models.auth.auth import (
    LoginUser,
    RecoveryPassword,
    RecoveryPasswordOtp,
    RegisterUser,
)
from core.brevio_api.models.responses.auth_response import (
    LoginDataResponse,
    LoginResponse,
    PasswordRecoveryDataResponse,
    PasswordRecoveryResponse,
    RegisterDataResponse,
    RegisterResponse,
    SessionDataResponse,
    SessionResponse,
)
from core.brevio_api.services.auth_cookies import (
    REFRESH_COOKIE_NAME,
    clear_auth_cookies,
    set_auth_cookies,
)
from core.brevio_api.services.auth_service import AuthService, AuthSession
from core.brevio_api.services.token_service import TokenService


def _cookie_response(
    status_code: int,
    content: dict,
    session: AuthSession,
) -> JSONResponse:
    response = JSONResponse(status_code=status_code, content=content)
    set_auth_cookies(
        response,
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        access_max_age=session.access_max_age,
        refresh_max_age=session.refresh_max_age,
    )
    return response


class AuthRoutes:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/auth", tags=["authentication"])
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.post(
            "/login",
            status_code=status.HTTP_200_OK,
            response_model=LoginDataResponse,
            description="Authenticate a user and set httpOnly access/refresh cookies",
            responses={
                401: {"description": "Invalid credentials"},
                422: {"description": "Validation error"},
            },
        )
        async def login(
            request: Request,
            login_user: LoginUser,
            auth_service: AuthService = Depends(get_auth_service),
        ) -> JSONResponse:
            from core.brevio_api.utils.rate_limit import enforce_auth_rate_limit

            enforce_auth_rate_limit(request, "login")
            session: AuthSession = await auth_service.login(login_user)
            response = LoginDataResponse(
                status="success",
                data=LoginResponse(authenticated=True),
            )
            return _cookie_response(status.HTTP_200_OK, response.model_dump(), session)

        @self.router.post(
            "/register",
            response_model=RegisterDataResponse,
            status_code=status.HTTP_201_CREATED,
            description="Register a new user account and set httpOnly cookies",
            responses={
                400: {"description": "User already exists"},
                422: {"description": "Validation error"},
            },
        )
        async def register(
            request: Request,
            register_user: RegisterUser,
            auth_service: AuthService = Depends(get_auth_service),
        ) -> JSONResponse:
            from core.brevio_api.utils.rate_limit import enforce_auth_rate_limit

            enforce_auth_rate_limit(request, "register")
            session: AuthSession = await auth_service.register(register_user)
            folder = session.folder
            if folder is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="La carpeta no se creó correctamente.",
                )
            response = RegisterDataResponse(
                status="success",
                data=RegisterResponse(folder=folder, authenticated=True),
            )
            return _cookie_response(
                status.HTTP_201_CREATED, response.model_dump(), session
            )

        @self.router.post(
            "/refresh",
            status_code=status.HTTP_200_OK,
            response_model=LoginDataResponse,
            description="Rotate the refresh cookie and issue a new access cookie",
        )
        async def refresh(
            request: Request,
            auth_service: AuthService = Depends(get_auth_service),
        ) -> JSONResponse:
            from core.brevio_api.utils.rate_limit import enforce_auth_rate_limit

            enforce_auth_rate_limit(request, "refresh")
            refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
            if not refresh_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token no proporcionado",
                )
            session = await auth_service.refresh(refresh_token)
            response = LoginDataResponse(
                status="success",
                data=LoginResponse(authenticated=True),
            )
            return _cookie_response(status.HTTP_200_OK, response.model_dump(), session)

        @self.router.post(
            "/logout",
            status_code=status.HTTP_200_OK,
            description="Revoke the refresh session and clear auth cookies",
        )
        async def logout(
            request: Request,
            auth_service: AuthService = Depends(get_auth_service),
        ) -> JSONResponse:
            from core.brevio_api.services.auth_cookies import ACCESS_COOKIE_NAME

            await auth_service.logout(
                request.cookies.get(REFRESH_COOKIE_NAME),
                access_token=request.cookies.get(ACCESS_COOKIE_NAME),
            )
            payload = {
                "status": "success",
                "data": {"authenticated": False},
            }
            response = JSONResponse(status_code=status.HTTP_200_OK, content=payload)
            clear_auth_cookies(response)
            return response

        @self.router.get(
            "/session",
            status_code=status.HTTP_200_OK,
            response_model=SessionDataResponse,
            description="Return whether the access cookie is currently valid",
        )
        async def session(
            request: Request,
            token_service: TokenService = Depends(get_token_service),
        ) -> SessionDataResponse:
            from core.brevio_api.services.auth_cookies import ACCESS_COOKIE_NAME

            token = request.cookies.get(ACCESS_COOKIE_NAME)
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token no proporcionado o nulo",
                )
            payload = token_service.validate_access_token(token)
            return SessionDataResponse(
                status="success",
                data=SessionResponse(
                    authenticated=True,
                    user_id=str(payload["id"]),
                ),
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
            request: Request,
            identity: RecoveryPassword,
            auth_service: AuthService = Depends(get_auth_service),
        ) -> PasswordRecoveryDataResponse:
            from core.brevio_api.utils.rate_limit import enforce_auth_rate_limit

            enforce_auth_rate_limit(request, "password_recovery")
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
            request: Request,
            recovery_password_otp: RecoveryPasswordOtp,
            response: Response,
            auth_service: AuthService = Depends(get_auth_service),
        ) -> PasswordRecoveryDataResponse:
            from core.brevio_api.utils.rate_limit import enforce_auth_rate_limit

            enforce_auth_rate_limit(request, "password_verify")
            recovery_password_response: PasswordRecoveryResponse = (
                await auth_service.change_password(recovery_password_otp)
            )
            clear_auth_cookies(response)
            return PasswordRecoveryDataResponse(
                status="success",
                data=recovery_password_response,
            )


auth_router = AuthRoutes().router
