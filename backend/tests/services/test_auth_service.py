from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import mongomock
import pytest
from bson import ObjectId
from fastapi import HTTPException

from backend.models.auth.auth import LoginUser, RegisterUser
from backend.models.user.user_folder import UserFolder
from backend.models.user.user_model import User
from backend.services.auth_service import AuthService
from backend.services.token_service import TokenService
from backend.services.user_service import UserService
from brevio.models.response_model import FolderResponse


@pytest.fixture
def mock_db():
    return mongomock.MongoClient().db


@pytest.fixture
def token_service():
    service = MagicMock(spec=TokenService)
    service.create_access_token = MagicMock(return_value="test_token")
    return service


@pytest.fixture
def user_service():
    service = MagicMock(spec=UserService)
    service.get_user_by_email = MagicMock()
    service.get_user_by_username = MagicMock()
    service.create_user = MagicMock()
    return service


@pytest.fixture
def auth_service(mock_db, token_service, user_service) -> AuthService:
    # Inyectar explícitamente el user_service en auth_service
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
    created_user = User(
        _id=mock_user_id,
        email=user_data["email"],
        username=user_data["username"],
        password="hashed_password",
        folder=folder,
    )

    user_service.get_user_by_email.return_value = None
    user_service.create_user.return_value = created_user

    with patch(
        "backend.services.auth_service.hash_password", return_value="hashed_password"
    ):
        with patch(
            "backend.services.auth_service.DirectoryManager"
        ) as mock_dir_manager:
            mock_dir_manager.return_value.createFolder.return_value = FolderResponse(
                success=True, message="Successfully created the directory 'test_folder'"
            )
            with patch(
                "backend.services.auth_service.isEmail", return_value=user_data["email"]
            ):
                with patch("backend.services.auth_service.EmailService") as mock_email:
                    mock_email.return_value.send_register_email = AsyncMock()
                    result = await auth_service.register(user)

    assert result.token == "test_token"
    assert isinstance(result.folder, FolderResponse)
    assert result.folder.success == True
    assert "Successfully created" in result.folder.message


@pytest.mark.asyncio
async def test_register_user_exists(
    auth_service: AuthService,
    user_data: Dict[str, Any],
    user_service: MagicMock,
    mock_user_id: ObjectId,
) -> None:
    folder = UserFolder(_id=ObjectId())
    existing_user = User(
        _id=mock_user_id,
        email=user_data["email"],
        username=user_data["username"],
        password="hashed_password",
        folder=folder,
    )
    new_user = RegisterUser(**user_data)

    user_service.get_user_by_email.return_value = existing_user

    with patch(
        "backend.services.auth_service.isEmail", return_value=user_data["email"]
    ):
        # Cambiar a HTTPException en lugar de ValueError
        with pytest.raises(HTTPException) as excinfo:
            await auth_service.register(new_user)

    assert excinfo.value.status_code == 400
    assert "User already exists" in str(excinfo.value.detail)
    # Cambiar a assert_called_once si no es una corrutina
    user_service.get_user_by_email.assert_called_once_with(new_user.email)


def test_login_success(
    auth_service: AuthService,
    user_data: Dict[str, Any],
    login_data: Dict[str, Any],
    user_service: MagicMock,
    mock_user_id: ObjectId,
) -> None:
    folder = UserFolder(_id=ObjectId(), entries=[])
    user = User(
        _id=mock_user_id,
        email=user_data["email"],
        username=user_data["username"],
        password="hashed_password",
        folder=folder,
    )
    user_login = LoginUser(**login_data)

    # Configura los mocks correctamente
    user_service.get_user_by_email.return_value = user
    user_service.get_user_by_username.return_value = None

    # Asegura que auth_service use este user_service
    auth_service._user_service = user_service

    with patch(
        "backend.services.auth_service.verify_password", return_value=True
    ) as mock_verify_password:
        # En lugar de mockear isEmail para devolver True, hazlo para devolver el mismo email
        # Es probable que la función isEmail solo valide el formato y devuelva el mismo email
        with patch(
            "backend.services.auth_service.isEmail", return_value=login_data["identity"]
        ):
            result = auth_service.login(user_login)

    # Verificaciones
    assert result.access_token == "test_token"

    # Verifica las llamadas a mocks sin los argumentos exactos si hay problemas
    assert mock_verify_password.called
    assert user_service.get_user_by_email.called

    # O verifica los argumentos de llamada con más detalle si es necesario
    mock_verify_password.assert_called_once_with(
        login_data["password"], "hashed_password"
    )
    user_service.get_user_by_email.assert_called_once_with(login_data["identity"])


def test_login_invalid_password(
    auth_service: AuthService,
    user_data: Dict[str, Any],
    login_data: Dict[str, Any],
    user_service: MagicMock,
    mock_user_id: ObjectId,
) -> None:
    folder = UserFolder(_id=ObjectId(), entries=[])
    user = User(
        _id=mock_user_id,
        email=user_data["email"],
        username=user_data["username"],
        password="hashed_password",
        folder=folder,
    )
    user_login = LoginUser(**login_data)

    user_service.get_user_by_email.return_value = user

    with patch(
        "backend.services.auth_service.verify_password", return_value=False
    ) as mock_verify_password:
        with patch("backend.services.auth_service.isEmail", return_value=True):
            with pytest.raises(HTTPException) as excinfo:
                auth_service.login(user_login)

            assert excinfo.value.status_code == 401
            assert "Contraseña incorrecta" in str(excinfo.value.detail)
            mock_verify_password.assert_called_once_with(
                user_login.password, user.password
            )
