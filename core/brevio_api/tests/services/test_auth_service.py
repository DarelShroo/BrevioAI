from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import bcrypt
import mongomock
import pytest
from bson import ObjectId
from fastapi import HTTPException
from pydantic import ValidationError

from core.brevio.models.response_model import FolderResponse
from core.brevio_api.models.auth.auth import (
    LoginUser,
    RecoveryPassword,
    RecoveryPasswordOtp,
    RegisterUser,
)
from core.brevio_api.models.user.user_folder import UserFolder
from core.brevio_api.models.user.user_model import User
from core.brevio_api.services.auth_service import AuthService
from core.brevio_api.services.token_service import TokenService
from core.brevio_api.services.user_service import UserService
from core.brevio_api.utils.password_utils import hash_password


@pytest.fixture
def mock_db() -> Any:
    return mongomock.MongoClient().db


@pytest.fixture
def token_service() -> MagicMock:
    service = MagicMock(spec=TokenService)
    service.create_access_token = MagicMock(return_value="test_token")
    return service


@pytest.fixture
def user_service() -> MagicMock:
    service = MagicMock(spec=UserService)
    service.get_user_by_email = AsyncMock()
    service.get_user_by_username = AsyncMock()
    service.create_user = AsyncMock()
    service.change_password = AsyncMock()
    return service


@pytest.fixture
def auth_service(
    mock_db: Any, token_service: TokenService, user_service: UserService
) -> AuthService:
    auth_service = AuthService(mock_db, token_service)
    auth_service._user_service = user_service
    return auth_service


@pytest.fixture
def user_data() -> Dict[str, Any]:
    return {
        "email": "test@example.com",
        "password": "Test_password1",
        "username": "testuser",
    }


@pytest.fixture
def login_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "identity": user_data["email"],
        "password": user_data["password"],
    }


@pytest.fixture
def mock_user_id() -> ObjectId:
    return ObjectId()


@pytest.mark.asyncio
async def test_register_success(
    auth_service: AuthService,
    user_data: Dict[str, Any],
    user_service: MagicMock,
    mock_user_id: ObjectId,
) -> None:
    user = RegisterUser(**user_data)
    folder = UserFolder(_id=ObjectId())
    valid_hashed_password = hash_password(user_data["password"])
    created_user = User(
        _id=mock_user_id,
        email=user_data["email"],
        username=user_data["username"],
        password=valid_hashed_password,
        folder=folder,
    )

    user_service.get_user_by_email.return_value = None
    user_service.create_user.return_value = created_user

    with patch(
        "core.brevio_api.utils.password_utils.hash_password",
        return_value=valid_hashed_password,
    ):
        with patch(
            "core.brevio.managers.directory_manager.DirectoryManager"
        ) as mock_dir_manager:
            mock_dir_manager.return_value.createFolder.return_value = FolderResponse(
                success=True, message="Successfully created the directory 'test_folder'"
            )
            with patch(
                "core.brevio_api.utils.email_utils.isEmail",
                return_value=user_data["email"],
            ):
                with patch(
                    "core.brevio_api.services.auth_service.EmailService"
                ) as mock_email:
                    mock_email.return_value.send_register_email = AsyncMock()
                    result = await auth_service.register(user)

    assert result.access_token == "test_token"
    assert isinstance(result.folder, FolderResponse)
    assert result.folder.success is True
    assert "Successfully created" in result.folder.message
    user_service.get_user_by_email.assert_awaited_once_with(user_data["email"])
    user_service.create_user.assert_awaited_once()
    mock_email.return_value.send_register_email.assert_awaited_once()


@pytest.mark.asyncio
async def test_login_user_not_found(
    auth_service: AuthService,
    user_data: Dict[str, Any],
    login_data: Dict[str, Any],
    user_service: MagicMock,
) -> None:
    user_login = LoginUser(**login_data)
    user_service.get_user_by_email.return_value = None
    with patch(
        "core.brevio_api.utils.email_utils.isEmail",
        return_value=user_data["email"],
    ):
        with pytest.raises(HTTPException) as excinfo:
            await auth_service.login(user_login)
    assert excinfo.value.status_code == 404
    assert "credenciales inválidas" in str(excinfo.value.detail).lower()
    user_service.get_user_by_email.assert_awaited_once_with(user_data["email"])


@pytest.mark.asyncio
async def test_login_success(
    auth_service: AuthService,
    user_data: Dict[str, Any],
    login_data: Dict[str, Any],
    user_service: MagicMock,
    mock_user_id: ObjectId,
) -> None:
    folder = UserFolder(_id=ObjectId(), entries=[])
    valid_hashed_password = hash_password(user_data["password"])
    user = User(
        _id=mock_user_id,
        email=user_data["email"],
        username=user_data["username"],
        password=valid_hashed_password,
        folder=folder,
    )
    user_login = LoginUser(**login_data)

    user_service.get_user_by_email.return_value = user
    user_service.get_user_by_username.return_value = None

    with patch(
        "core.brevio_api.utils.email_utils.isEmail",
        return_value=user_data["email"],
    ):
        with patch(
            "core.brevio_api.services.auth_service.verify_password",
            side_effect=lambda x, y: True,
        ) as mock_verify_password:
            result = await auth_service.login(user_login)

    assert result.access_token == "test_token"
    mock_verify_password.assert_called_once_with(
        login_data["password"], valid_hashed_password
    )
    user_service.get_user_by_email.assert_awaited_once_with(user_data["email"])


@pytest.mark.asyncio
async def test_login_invalid_password(
    auth_service: AuthService,
    user_data: Dict[str, Any],
    login_data: Dict[str, Any],
    user_service: MagicMock,
    mock_user_id: ObjectId,
) -> None:
    folder = UserFolder(_id=ObjectId(), entries=[])
    valid_hashed_password = hash_password(user_data["password"])
    user = User(
        _id=mock_user_id,
        email=user_data["email"],
        username=user_data["username"],
        password=valid_hashed_password,
        folder=folder,
    )
    user_login = LoginUser(**login_data)

    user_service.get_user_by_email.return_value = user
    user_service.get_user_by_username.return_value = None

    with patch(
        "core.brevio_api.utils.email_utils.isEmail",
        return_value=user_data["email"],
    ):
        with patch(
            "core.brevio_api.services.auth_service.verify_password",
            side_effect=lambda x, y: False,
        ) as mock_verify_password:
            with pytest.raises(HTTPException) as excinfo:
                await auth_service.login(user_login)

    assert excinfo.value.status_code == 401
    assert "Credenciales inválidas" in str(excinfo.value.detail)
    mock_verify_password.assert_called_once_with(
        login_data["password"], valid_hashed_password
    )
    user_service.get_user_by_email.assert_awaited_once_with(user_data["email"])


@pytest.mark.asyncio
async def test_password_recovery_handshake(
    auth_service: AuthService,
    user_data: Dict[str, Any],
    user_service: MagicMock,
    mock_user_id: ObjectId,
) -> None:
    folder = UserFolder(_id=ObjectId())
    valid_hashed_password = hash_password(user_data["password"])
    user = User(
        _id=mock_user_id,
        email=user_data["email"],
        username=user_data["username"],
        password=valid_hashed_password,
        folder=folder,
        otp=None,
        exp=None,
    )
    recovery_data = RecoveryPassword(identity=user_data["email"])

    user_service.get_user_by_email.return_value = user

    with patch(
        "core.brevio_api.utils.email_utils.isEmail", return_value=user_data["email"]
    ):
        with patch(
            "core.brevio_api.utils.otp_utils.OTPUtils.generate_otp",
            return_value="123456",
        ):
            with patch(
                "core.brevio_api.services.auth_service.EmailService"
            ) as mock_email:
                mock_email.return_value.send_recovery_password_email = AsyncMock()
                with patch.object(
                    auth_service._user_repository, "update_user", AsyncMock()
                ) as mock_update_user:
                    result = await auth_service.password_recovery_handshake(
                        recovery_data
                    )

    assert result.message == "Código de recuperación enviado al correo electrónico."
    user_service.get_user_by_email.assert_awaited_once_with(user_data["email"])
    mock_update_user.assert_awaited_once()
    mock_email.return_value.send_recovery_password_email.assert_awaited_once_with(
        "123456"
    )


@pytest.mark.asyncio
async def test_change_password(
    auth_service: AuthService,
    user_data: Dict[str, Any],
    user_service: MagicMock,
    mock_user_id: ObjectId,
) -> None:
    """Test changing password with valid OTP."""
    folder = UserFolder(_id=ObjectId())
    valid_hashed_password = hash_password(user_data["password"])
    exp_time = int((datetime.now() + timedelta(minutes=5)).timestamp())
    user = User(
        _id=mock_user_id,
        email=user_data["email"],
        username=user_data["username"],
        password=valid_hashed_password,
        folder=folder,
        otp=123456,
        exp=exp_time,
    )
    recovery_otp = RecoveryPasswordOtp(
        email=user_data["email"], otp=123456, password="New_password1"
    )

    user_service.get_user_by_email.return_value = user

    with patch("core.brevio_api.services.auth_service.EmailService") as mock_email:
        mock_email.return_value.send_password_changed_email = AsyncMock()
        result = await auth_service.change_password(recovery_otp)

    assert result.message == "Contraseña cambiada exitosamente."
    user_service.get_user_by_email.assert_awaited_once_with(user_data["email"])
    user_service.change_password.assert_awaited_once_with(
        user_data["email"], recovery_otp.password
    )
    mock_email.return_value.send_password_changed_email.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_password_invalid_otp(
    auth_service: AuthService,
    user_data: Dict[str, Any],
    user_service: MagicMock,
    mock_user_id: ObjectId,
) -> None:
    folder = UserFolder(_id=ObjectId())
    valid_hashed_password = hash_password(user_data["password"])
    exp_time = int((datetime.now() + timedelta(minutes=5)).timestamp())
    user = User(
        _id=mock_user_id,
        email=user_data["email"],
        username=user_data["username"],
        password=valid_hashed_password,
        folder=folder,
        otp=123456,
        exp=exp_time,
    )
    recovery_otp = RecoveryPasswordOtp(
        email=user_data["email"], otp=654321, password="New_password1"
    )

    user_service.get_user_by_email.return_value = user

    with patch("core.brevio_api.services.auth_service.EmailService") as mock_email:
        mock_email.return_value.send_password_changed_email = AsyncMock()
        with pytest.raises(HTTPException) as excinfo:
            await auth_service.change_password(recovery_otp)

    assert excinfo.value.status_code == 400
    assert "El código de recuperación es incorrecto." in str(excinfo.value.detail)
    user_service.get_user_by_email.assert_awaited_once_with(user_data["email"])
