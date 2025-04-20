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
from core.brevio_api.models.responses.auth_response import (
    LoginResponse,
    PasswordRecoveryResponse,
    RegisterResponse,
)

# Stub service providing default successful responses
default_folder = FolderResponse(success=True, message="folder created")


class StubAuthService:
    def login(self, login_user: LoginUser) -> LoginResponse:
        return LoginResponse(access_token="testtoken")

    async def register(self, register_user: RegisterUser) -> RegisterResponse:
        return RegisterResponse(folder=default_folder, token="testtoken")

    async def password_recovery_handshake(
        self, recovery_password: RecoveryPassword
    ) -> PasswordRecoveryResponse:
        return PasswordRecoveryResponse(message="Código de recuperación enviado.")

    async def change_password(
        self, recovery_password_otp: RecoveryPasswordOtp
    ) -> PasswordRecoveryResponse:
        return PasswordRecoveryResponse(message="Contraseña cambiada exitosamente.")


@pytest.fixture(autouse=True)
def override_auth_service() -> Any:
    """Override the AuthService dependency with a stub for all tests by default."""
    app.dependency_overrides[get_auth_service] = lambda: StubAuthService()
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


def test_login_success() -> None:
    payload = {"identity": "user123", "password": "Aa1@aaa!"}
    response = client.post("/auth/login", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["access_token"] == "testtoken"


def test_login_invalid_credentials() -> None:
    class ErrorAuthService(StubAuthService):
        def login(self, login_user: LoginUser) -> LoginResponse:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Contraseña incorrecta"
            )

    app.dependency_overrides[get_auth_service] = lambda: ErrorAuthService()
    response = client.post(
        "/auth/login", json={"identity": "user123", "password": "Wr@ng1Pass!"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["message"] == "Contraseña incorrecta"


def test_login_validation_error_missing_field() -> None:
    # Missing password field should trigger validation error
    response = client.post("/auth/login", json={"identity": "user123"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ----- Registration tests -----


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
    assert data["data"]["token"] == "testtoken"
    assert data["data"]["folder"]["success"] is True


def test_register_user_exists() -> None:
    class ErrorAuthService(StubAuthService):
        async def register(self, register_user: RegisterUser) -> RegisterResponse:
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
    # Missing email field
    response = client.post(
        "/auth/register", json={"username": "user123", "password": "Aa1@aaa!"}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ----- Password recovery handshake tests -----


def test_password_recovery_handshake_success() -> None:
    payload = {"identity": "user123"}
    response = client.post("/auth/password-recovery-handshake", json=payload)
    print(response)
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
                status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado."
            )

    app.dependency_overrides[get_auth_service] = lambda: ErrorAuthService()
    payload = {"identity": "unknown"}
    response = client.post("/auth/password-recovery-handshake", json=payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["message"] == "Usuario no encontrado."


def test_password_recovery_handshake_validation_error_missing_field() -> None:
    # Missing identity field
    response = client.post("/auth/password-recovery-handshake", json={})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ----- Password recovery verify tests -----


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
    # Missing otp field
    response = client.post(
        "/auth/password-recovery-verify",
        json={"email": "user@example.com", "password": "NewPass1!"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_method_not_allowed_for_login() -> None:
    response = client.get("/auth/login")
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
