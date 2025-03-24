from bson import ObjectId
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from pydantic import ValidationError
from ...services.auth_service import AuthService
from ...models.auth import LoginUser, RegisterUser, RecoveryPassword, RecoveryPasswordOtp
from ...models.user import User, UserFolder
from ...utils.password_utils import hash_password
from ...services.email_service import EmailService
from datetime import datetime, timedelta
from ...utils.email_utils import isEmail
from ...utils.password_utils import verify_password
import pytest

password = "A123@password"
email = "test@example.com"
username = "test_user"
hashed_password = hash_password(password)


@pytest.fixture
def auth_service(mocker):
    """Should provide an instance of AuthService with mocked dependencies."""
    mock_user_repository_instance = MagicMock()
    mocker.patch(
        'backend.services.auth_service.UserRepository',
        return_value=mock_user_repository_instance
    )

    db_mock = MagicMock()
    token_service_mock = MagicMock()

    auth_service = AuthService(db=db_mock, token_service=token_service_mock)

    auth_service._user_repository = mock_user_repository_instance
    auth_service._user_service = mocker.MagicMock()
    auth_service.directory_manager = mocker.MagicMock()

    return auth_service


@pytest.mark.asyncio
async def test_login_success_username(auth_service, mocker):
    """Should successfully log in a user using username."""
    user_mock = User(
        id=ObjectId(), 
        username=username, 
        email=email,
        password=hashed_password, 
        folder=UserFolder(id=ObjectId(), entries=[])
    )

    # Should detect that the identity is not an email.
    mocker.patch('backend.utils.email_utils.isEmail', return_value=False)
    auth_service._user_service.get_user_by_username.return_value = user_mock
    # Should verify the password correctly.
    mocker.patch('backend.utils.password_utils.verify_password', return_value=True)
    auth_service._token_service.create_access_token.return_value = "mock_token"

    result = await auth_service.login(LoginUser(identity=username, password=password))

    # Should return the expected username and token.
    assert result == {"username": username, "token": "mock_token"}
    auth_service._user_service.get_user_by_username.assert_called_once_with(username)
    auth_service._token_service.create_access_token.assert_called_once()


@pytest.mark.asyncio
async def test_login_success_email(auth_service, mocker):
    """Should successfully log in a user using email."""
    user_mock = User(
        id=ObjectId(), 
        username="test_user", 
        email=email,
        password=hashed_password, 
        folder=UserFolder(id=ObjectId(), entries=[])
    )

    # Should detect that the identity is an email.
    mocker.patch('backend.utils.email_utils.isEmail', return_value=True)
    auth_service._user_service.get_user_by_email.return_value = user_mock
    # Should verify the password correctly.
    mocker.patch('backend.utils.password_utils.verify_password', return_value=True)
    auth_service._token_service.create_access_token.return_value = "mock_token"

    result = await auth_service.login(LoginUser(identity=email, password=password))
    # Should return the correct username and token.
    assert result["username"] == username
    assert result["token"] == "mock_token"


@pytest.mark.asyncio
async def test_login_user_not_found(auth_service, mocker):
    """Should raise an HTTPException (404) when the user is not found."""
    mocker.patch('backend.utils.email_utils.isEmail', return_value=False)
    auth_service._user_service.get_user_by_username.return_value = None

    with pytest.raises(HTTPException) as exc:
        await auth_service.login(LoginUser(identity="unknown", password=password))
    # Should raise a 404 error with the message "Usuario no encontrado".
    assert exc.value.status_code == 404
    assert exc.value.detail == "Usuario no encontrado"


@pytest.mark.asyncio
async def test_login_incorrect_password(auth_service, mocker):
    """Should raise an HTTPException (401) when the password is incorrect."""
    user_mock = User(
        id=ObjectId(), 
        username=username, 
        email=email,
        password=hashed_password, 
        folder=UserFolder(id=ObjectId(), entries=[])
    )
    mocker.patch('backend.utils.email_utils.isEmail', return_value=False)
    auth_service._user_service.get_user_by_username.return_value = user_mock
    # Should fail password verification.
    mocker.patch('backend.utils.password_utils.verify_password', return_value=False)

    with pytest.raises(HTTPException) as exc:
        await auth_service.login(LoginUser(identity=username, password="wrongA23@PASSWORD"))
    # Should raise a 401 error with the message "Contraseña incorrecta".
    assert exc.value.status_code == 401
    assert exc.value.detail == "Contraseña incorrecta"


@pytest.mark.asyncio
async def test_register_success(auth_service, mocker):
    """Should successfully register a new user."""
    user_register = RegisterUser(username=username, email=email, password=password)

    user_mock = User(
        id=ObjectId(),
        username=username,
        email=email,
        password=hashed_password,
        folder=UserFolder(id=ObjectId(), entries=[])
    )

    auth_service._user_service.create_user.return_value = user_mock
    auth_service.directory_manager.createFolder.return_value = "folder_created"
    mocker.patch('os.path.exists', return_value=False)
    # Should send a registration email asynchronously.
    mocker.patch('backend.services.email_service.EmailService.send_register_email', new_callable=AsyncMock)
    auth_service._token_service.create_access_token.return_value = "mock_token"

    result = await auth_service.register(user_register)

    # Should return the folder destination and token.
    assert result == {"folder_dest": "folder_created", "token": "mock_token"}
    auth_service._user_service.create_user.assert_called_once()
    auth_service.directory_manager.createFolder.assert_called_once()
    EmailService.send_register_email.assert_called_once()


@pytest.mark.asyncio
async def test_register_user_already_exists(auth_service, mocker):
    """Should raise an HTTPException (400) when the user already exists."""
    user_register = RegisterUser(username="existing_user", email=email, password=password)
    auth_service._user_service.create_user.side_effect = ValueError("User already exists")

    with pytest.raises(HTTPException) as exc:
        await auth_service.register(user_register)
    # Should raise a 400 error with a message indicating the user already exists.
    assert exc.value.status_code == 400
    assert "Error al registrar usuario: User already exists" in exc.value.detail


@pytest.mark.asyncio
async def test_register_validation_error(auth_service, mocker):
    """Should raise a ValidationError when registration data is invalid."""
    invalid_email = "invalid-email"
    with pytest.raises(ValidationError) as exc_info:
        RegisterUser(username=username, email=invalid_email, password=password)

    # Should indicate that the email address is not valid.
    assert "value is not a valid email address" in str(exc_info.value)


@pytest.mark.asyncio
async def test_password_recovery_handshake_new_otp(auth_service, mocker):
    """Should send a new OTP for password recovery when the user exists."""
    user_mock = User(
        id=ObjectId(), 
        username=username, 
        email=email,
        password=hashed_password, 
        folder=UserFolder(id=ObjectId(), entries=[])
    )
    mocker.patch('backend.utils.email_utils.isEmail', return_value=True)
    auth_service._user_service.get_user_by_email.return_value = user_mock
    mocker.patch('backend.utils.otp_utils.OTPUtils.generate_otp', return_value="123456")
    # Should send the recovery password email asynchronously.
    mocker.patch('backend.services.email_service.EmailService.send_recovery_password_email', new_callable=AsyncMock)
    auth_service._user_repository.password_recovery_handshake.return_value = None

    result = await auth_service.password_recovery_handshake(RecoveryPassword(identity=email))

    # Should return a confirmation message that the recovery code was sent.
    assert result == {"detail": "Código de recuperación enviado al correo electrónico."}
    auth_service._user_repository.password_recovery_handshake.assert_called_once()
    EmailService.send_recovery_password_email.assert_called_once_with("123456")


@pytest.mark.asyncio
async def test_password_recovery_handshake_otp_valid(auth_service, mocker):
    """Should not resend OTP if a valid OTP already exists."""
    user_mock = User(
        id=ObjectId(),
        username=username,
        email=email,
        password=hashed_password,
        folder=UserFolder(id=ObjectId(), entries=[]),
        otp="123456",
        # OTP no ha expirado.
        exp=int((datetime.now() + timedelta(minutes=10)).timestamp())
    )
    mocker.patch('backend.utils.email_utils.isEmail', return_value=True)
    auth_service._user_service.get_user_by_email.return_value = user_mock

    mock_send_email = mocker.patch.object(
        EmailService, 'send_recovery_password_email', new_callable=AsyncMock, return_value=None)

    result = await auth_service.password_recovery_handshake(RecoveryPassword(identity=email))

    # Should not resend the OTP if the current one is still valid.
    mock_send_email.assert_not_called()


@pytest.mark.asyncio
async def test_password_recovery_handshake_user_not_found(auth_service, mocker):
    """Should raise an HTTPException (404) when the user is not found during password recovery."""
    mocker.patch('backend.utils.email_utils.isEmail', return_value=True)
    auth_service._user_service.get_user_by_email.return_value = None

    with pytest.raises(HTTPException) as exc:
        await auth_service.password_recovery_handshake(RecoveryPassword(identity="unknown@example.com"))
    # Should raise a 404 error indicating the user was not found.
    assert exc.value.status_code == 404
    assert exc.value.detail == "Usuario no encontrado."


@pytest.mark.asyncio
async def test_change_password_success(auth_service, mocker):
    """Should successfully change the user's password when provided with a valid OTP."""
    user_mock = User(
        id=ObjectId(),
        email=email,
        password=hashed_password,
        otp="123456",
        exp=int((datetime.now() + timedelta(minutes=5)).timestamp()),
        folder=UserFolder(id=ObjectId(), entries=[])
    )

    mocker.patch('backend.utils.email_utils.isEmail', return_value=True)

    auth_service._user_service.get_user_by_email.return_value = user_mock
    auth_service._user_service.change_password = AsyncMock(return_value=None)

    mocked_email_service = mocker.patch(
        'backend.services.email_service.EmailService.send_password_changed_email',
        new_callable=AsyncMock
    )

    result = await auth_service.change_password(
        RecoveryPasswordOtp(email=email, otp="123456", password=password)
    )

    # Should return a success message indicating the password was changed.
    assert result == {"detail": "Contraseña cambiada exitosamente."}
    auth_service._user_service.change_password.assert_called_once_with(email, password)
    mocked_email_service.assert_called_once()


@pytest.mark.asyncio
async def test_change_password_otp_expired(auth_service, mocker):
    """Should raise an HTTPException (400) when the OTP has expired."""
    user_mock = User(
        id=ObjectId(), 
        email=email, 
        password=hashed_password,
        otp="123456", 
        exp=int((datetime.now() - timedelta(minutes=1)).timestamp()),
        folder=UserFolder(id=ObjectId(), entries=[])
    )
    mocker.patch('backend.utils.email_utils.isEmail', return_value=True)
    auth_service._user_service.get_user_by_email.return_value = user_mock

    with pytest.raises(HTTPException) as exc:
        await auth_service.change_password(RecoveryPasswordOtp(email=email, otp="123456", password=password))
    # Should raise a 400 error indicating that the recovery code has expired.
    assert exc.value.status_code == 400
    assert exc.value.detail == "El código de recuperación ha expirado."


@pytest.mark.asyncio
async def test_change_password_invalid_otp(auth_service, mocker):
    """Should raise an HTTPException (400) when an invalid OTP is provided."""
    user_mock = User(
        id=ObjectId(), 
        email=email, 
        otp="123456", 
        password=hashed_password,
        exp=int((datetime.now() + timedelta(minutes=5)).timestamp()),
        folder=UserFolder(id=ObjectId(), entries=[])
    )
    mocker.patch('backend.utils.email_utils.isEmail', return_value=True)
    auth_service._user_service.get_user_by_email.return_value = user_mock

    with pytest.raises(HTTPException) as exc:
        await auth_service.change_password(RecoveryPasswordOtp(email=email, otp="654321", password=password))
    # Should raise a 400 error indicating that the provided recovery code is incorrect.
    assert exc.value.status_code == 400
    assert exc.value.detail == "El código de recuperación es incorrecto."


@pytest.mark.asyncio
async def test_change_password_user_not_found(auth_service, mocker):
    """Should raise an HTTPException (404) when the user does not exist during password change."""
    mocker.patch('backend.utils.email_utils.isEmail', return_value=True)
    auth_service._user_service.get_user_by_email.return_value = None

    with pytest.raises(HTTPException) as exc:
        await auth_service.change_password(RecoveryPasswordOtp(email="unknown@example.com", otp="123456", password=password))
    # Should raise a 404 error indicating that the user does not exist.
    assert exc.value.status_code == 404
    assert exc.value.detail == "Usuario no existe"
