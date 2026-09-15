from typing import Any

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from core.brevio.models.response_model import FolderResponse
from core.brevio_api.__main__ import app
from core.brevio_api.dependencies.auth_service_dependency import get_auth_service
from core.brevio_api.models.auth.auth import (
    LoginUser,
    RecoveryPassword,
    RecoveryPasswordOtp,
    RegisterUser,
)
from core.brevio_api.models.responses.auth_response import PasswordRecoveryResponse
from core.brevio_api.services.auth_cookies import (
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
)
from core.brevio_api.services.auth_service import AuthSession

default_folder = FolderResponse(success=True, message="folder created")


def _session(folder: FolderResponse | None = None) -> AuthSession:
    return AuthSession(
        access_token="access-token",
        refresh_token="refresh-token",
        access_max_age=900,
        refresh_max_age=604800,
        folder=folder,
    )


class StubAuthService:
    async def login(self, login_user: LoginUser) -> AuthSession:
        return _session()

    async def register(self, register_user: RegisterUser) -> AuthSession:
        return _session(default_folder)

    async def refresh(self, refresh_token: str) -> AuthSession:
        return _session()

    async def logout(self, refresh_token: str | None) -> None:
        return None

    async def password_recovery_handshake(
        self, recovery_password: RecoveryPassword
    ) -> PasswordRecoveryResponse:
        return PasswordRecoveryResponse(message="Código de recuperación enviado.")

    async def change_password(
        self, recovery_password_otp: RecoveryPasswordOtp
    ) -> PasswordRecoveryResponse:
        return PasswordRecoveryResponse(message="Contraseña cambiada exitosamente.")


client = TestClient(app)


@pytest.fixture(autouse=True)
def override_auth_service() -> Any:
    app.dependency_overrides[get_auth_service] = lambda: StubAuthService()
    client.cookies.clear()
    yield
    app.dependency_overrides.clear()
    client.cookies.clear()


def _cookie_header(response: Any, name: str) -> str:
    headers = response.headers
    if hasattr(headers, "get_list"):
        items = headers.get_list("set-cookie")
    elif hasattr(headers, "getlist"):
        items = headers.getlist("set-cookie")
    else:
        value = headers.get("set-cookie")
        items = [value] if value else []
    match = next((item for item in items if item.startswith(f"{name}=")), "")
    assert match, f"missing {name} cookie in {items}"
    return match


def test_login_success() -> None:
    payload = {"identity": "user123", "password": "Aa1@aaa!"}
    response = client.post("/auth/login", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["authenticated"] is True
    assert "access_token" not in data["data"]
    access = _cookie_header(response, ACCESS_COOKIE_NAME)
    refresh = _cookie_header(response, REFRESH_COOKIE_NAME)
    assert "HttpOnly" in access
    assert "HttpOnly" in refresh
    assert "samesite=strict" in access.lower()
    assert "samesite=strict" in refresh.lower()
    assert ACCESS_COOKIE_NAME in response.cookies
    assert REFRESH_COOKIE_NAME in response.cookies


def test_login_invalid_credentials() -> None:
    class ErrorAuthService(StubAuthService):
        async def login(self, login_user: LoginUser) -> AuthSession:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas",
            )

    app.dependency_overrides[get_auth_service] = lambda: ErrorAuthService()
    response = client.post(
        "/auth/login", json={"identity": "user123", "password": "Wr@ng1Pass!"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["message"] == "Credenciales inválidas"


def test_login_validation_error_missing_field() -> None:
    response = client.post("/auth/login", json={"identity": "user123"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_register_success() -> None:
    payload = {
        "username": "user123",
        "email": "user@example.com",
        "password": "Aa1@aaa!",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["authenticated"] is True
    assert "access_token" not in data["data"]
    assert data["data"]["folder"]["success"] is True
    assert ACCESS_COOKIE_NAME in response.cookies


def test_refresh_rotates_cookies() -> None:
    response = client.post(
        "/auth/refresh", cookies={REFRESH_COOKIE_NAME: "refresh-token"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["authenticated"] is True
    assert ACCESS_COOKIE_NAME in response.cookies


def test_refresh_requires_cookie() -> None:
    response = client.post("/auth/refresh")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_logout_clears_cookies() -> None:
    response = client.post(
        "/auth/logout", cookies={REFRESH_COOKIE_NAME: "refresh-token"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["authenticated"] is False
    access = _cookie_header(response, ACCESS_COOKIE_NAME)
    assert "max-age=0" in access.lower() or "max-age=0" in access


def test_register_user_exists() -> None:
    class ErrorAuthService(StubAuthService):
        async def register(self, register_user: RegisterUser) -> AuthSession:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists"
            )

    app.dependency_overrides[get_auth_service] = lambda: ErrorAuthService()
    payload = {
        "username": "user123",
        "email": "user@example.com",
        "password": "Aa1@aaa!",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["message"] == "User already exists"


def test_register_validation_error_missing_field() -> None:
    response = client.post(
        "/auth/register", json={"username": "user123", "password": "Aa1@aaa!"}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_password_recovery_handshake_success() -> None:
    payload = {"identity": "test-success@gmail.com"}
    response = client.post("/auth/password-recovery-handshake", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["message"] == "Código de recuperación enviado."


def test_password_recovery_handshake_user_not_found() -> None:
    class ErrorAuthService(StubAuthService):
        async def password_recovery_handshake(
            self, recovery_password: RecoveryPassword
        ) -> PasswordRecoveryResponse:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Credenciales inválidas."
            )

    app.dependency_overrides[get_auth_service] = lambda: ErrorAuthService()
    payload = {"identity": "test-not-found@gmail.com"}
    response = client.post("/auth/password-recovery-handshake", json=payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["message"] == "Credenciales inválidas."


def test_password_recovery_handshake_validation_error_missing_field() -> None:
    response = client.post("/auth/password-recovery-handshake", json={})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_password_recovery_verify_success() -> None:
    payload = {"email": "user@example.com", "otp": "123456", "password": "NewPass1!"}
    response = client.post("/auth/password-recovery-verify", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["message"] == "Contraseña cambiada exitosamente."


def test_password_recovery_verify_invalid_otp() -> None:
    class ErrorAuthService(StubAuthService):
        async def change_password(
            self, recovery_password_otp: RecoveryPasswordOtp
        ) -> PasswordRecoveryResponse:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El código de recuperación es incorrecto.",
            )

    app.dependency_overrides[get_auth_service] = lambda: ErrorAuthService()
    payload = {"email": "user@example.com", "otp": "000000", "password": "NewPass1!"}
    response = client.post("/auth/password-recovery-verify", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["message"] == "El código de recuperación es incorrecto."


def test_password_recovery_verify_user_not_found() -> None:
    class ErrorAuthService(StubAuthService):
        async def change_password(
            self, recovery_password_otp: RecoveryPasswordOtp
        ) -> PasswordRecoveryResponse:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no existe"
            )

    app.dependency_overrides[get_auth_service] = lambda: ErrorAuthService()
    payload = {"email": "wrong@example.com", "otp": "123456", "password": "NewPass1!"}
    response = client.post("/auth/password-recovery-verify", json=payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["message"] == "Usuario no existe"


def test_password_recovery_verify_validation_error_missing_field() -> None:
    response = client.post(
        "/auth/password-recovery-verify",
        json={"email": "user@example.com", "password": "NewPass1!"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_method_not_allowed_for_login() -> None:
    response = client.get("/auth/login")
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
