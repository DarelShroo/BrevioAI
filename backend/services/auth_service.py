# Stdlib imports
from datetime import datetime, timedelta
from os import path
from typing import Any, Dict, Optional, Union, cast

# Third-party imports
from fastapi import HTTPException, status
from pymongo.database import Database

# Local imports
from backend.brevio.constants.constants import Constants
from backend.brevio.managers.directory_manager import DirectoryManager
from backend.brevio.models.response_model import FolderResponse
from backend.models.auth import RecoveryPassword, RecoveryPasswordOtp
from backend.models.auth.auth import LoginUser, RegisterUser
from backend.models.errors import AuthServiceException
from backend.models.user import UserFolder
from backend.models.user.user_model import User
from backend.repositories.folder_entry_repository import FolderEntryRepository
from backend.repositories.user_repository import UserRepository
from backend.services.email_service import EmailService
from backend.services.token_service import TokenService
from backend.services.user_service import UserService
from backend.utils.email_utils import isEmail
from backend.utils.otp_utils import OTPUtils
from backend.utils.password_utils import hash_password, verify_password
from models.responses.auth_response import (
    LoginResponse,
    PasswordRecoveryResponse,
    RegisterResponse,
)


class AuthService:
    def __init__(self, db: Database, token_service: TokenService):
        self._db = db
        self._user_repository = UserRepository(self._db)
        self._folder_entry_repository = FolderEntryRepository(self._db)
        self._user_service = UserService(
            self._user_repository, self._folder_entry_repository
        )
        self._token_service = token_service
        self.directory_manager = DirectoryManager()

    def login(self, user_login: LoginUser) -> LoginResponse:
        user: Optional[User] = None
        try:
            validated_email = isEmail(user_login.identity)
            user = self._user_service.get_user_by_email(validated_email)
        except ValueError:
            user = self._user_service.get_user_by_username(user_login.identity)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
            )

        if not verify_password(user_login.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Contraseña incorrecta"
            )

        token = self._token_service.create_access_token(
            {
                "id": str(user.id),
                "folder_id": str(user.folder.id),
            },
            timedelta(hours=1),
        )

        response = LoginResponse(access_token=token)
        return response

    async def register(self, user_register: RegisterUser) -> RegisterResponse:
        validated_email = isEmail(user_register.email)
        hashed_password = hash_password(user_register.password.strip())
        user_folder = UserFolder()

        existing_user = self._user_service.get_user_by_email(validated_email)

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists"
            )

        user = User(
            username=user_register.username,
            email=validated_email,
            password=hashed_password,
            folder=user_folder,
        )

        user_db: User = self._user_service.create_user(user)

        dest_folder = path.join(
            ".", Constants.DESTINATION_FOLDER, str(user_db.folder.id)
        )

        if not path.exists(dest_folder):
            folder_response: FolderResponse = self.directory_manager.createFolder(
                dest_folder
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La carpeta ya existe. No se puede crear una nueva.",
            )

        token: str = self._token_service.create_access_token(
            {
                "id": str(user.id),
                "folder_id": str(user.folder.id),
            },
            timedelta(hours=1),
        )

        email_service = EmailService(
            user_db.email, f"Usuario {user_db.username} registrado en Brevio"
        )

        await email_service.send_register_email()

        response = RegisterResponse(folder=folder_response, token=token)

        return response

    async def password_recovery_handshake(
        self, recovery_password_user: RecoveryPassword
    ) -> PasswordRecoveryResponse:
        user = None
        if isEmail(recovery_password_user.identity):
            user = self._user_service.get_user_by_email(recovery_password_user.identity)
        else:
            user = self._user_service.get_user_by_username(
                recovery_password_user.identity
            )

        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")

        now = datetime.now()

        if not user.otp or not user.exp or user.exp < int(now.timestamp()):
            otp = OTPUtils.generate_otp()
            new_time = now + timedelta(minutes=10)

            self._user_repository.update_user(
                user.id, {"otp": otp, "exp": int(new_time.timestamp())}
            )

            email_service = EmailService(user.email, "Recuperación de contraseña")

            await email_service.send_recovery_password_email(str(otp))

            response = PasswordRecoveryResponse(
                message="Código de recuperación enviado al correo electrónico."
            )

            return response

        response = PasswordRecoveryResponse(
            message="El código de recuperación ya fue enviado."
        )

        return response

    async def change_password(
        self, recovery_password_otp: RecoveryPasswordOtp
    ) -> Dict[str, str]:
        user = self._user_service.get_user_by_email(recovery_password_otp.email)

        if not user:
            raise HTTPException(status_code=404, detail="Usuario no existe")

        if not user.exp or user.exp < int(datetime.now().timestamp()):
            detail_message = (
                "El código de recuperación ya fue utilizado."
                if user.exp == 0
                else "El código de recuperación ha expirado."
            )
            raise HTTPException(status_code=400, detail=detail_message)

        if user.otp != recovery_password_otp.otp:
            raise HTTPException(
                status_code=400, detail="El código de recuperación es incorrecto."
            )

        self._user_service.change_password(user.email, recovery_password_otp.password)

        email_service = EmailService(user.email, "Confirmación de cambio de contraseña")

        await email_service.send_password_changed_email()

        response = PasswordRecoveryResponse(message="Contraseña cambiada exitosamente.")

        return response
