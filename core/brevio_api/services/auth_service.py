import logging
from datetime import datetime, timedelta
from os import path
from typing import Optional

from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import ValidationError

from core.brevio.constants.constants import Constants
from core.brevio.managers.directory_manager import DirectoryManager
from core.brevio.models.response_model import FolderResponse
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
from core.brevio_api.models.user.user_folder import UserFolder
from core.brevio_api.models.user.user_model import User
from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository
from core.brevio_api.repositories.user_repository import UserRepository
from core.brevio_api.services.email_service import EmailService
from core.brevio_api.services.token_service import TokenService
from core.brevio_api.services.user_service import UserService
from core.brevio_api.utils.email_utils import isEmail
from core.brevio_api.utils.otp_utils import OTPUtils
from core.brevio_api.utils.password_utils import hash_password, verify_password

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, collection: AsyncIOMotorCollection, token_service: TokenService):
        self._db = collection
        self._user_repository = UserRepository(self._db.get_collection("users"))
        self._folder_entry_repository = FolderEntryRepository(
            self._db.get_collection("entries")
        )
        self._user_service = UserService(
            self._user_repository, self._folder_entry_repository
        )
        self._token_service = token_service
        self.directory_manager = DirectoryManager()

    async def login(self, user_login: LoginUser) -> LoginResponse:
        user: User | None = None

        if isEmail(user_login.identity):
            validated_email = user_login.identity
            logger.debug(f"Validated email: {validated_email}")
            user = await self._user_service.get_user_by_email(validated_email)
        else:
            logger.debug(f"Email invalid, trying username: {user_login.identity}")
            user = await self._user_service.get_user_by_username(user_login.identity)

        if not user:
            logger.info(f"User not found for identity: {user_login.identity}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Credenciales Inválidas"
            )

        if not hasattr(user, "password") or user.password is None:
            logger.error(f"User {user.email} has no password set")
            raise HTTPException(status_code=500, detail="Datos de usuario inválidos")

        logger.debug(f"Verifying password for user: {user.email}")

        if not verify_password(user_login.password, user.password):
            logger.info(f"Password verification failed for user: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas",
            )

        logger.debug(f"Password verified, creating token for user: {user.email}")
        token = self._token_service.create_access_token(
            {"id": str(user.id)},
            timedelta(hours=1),
        )
        logger.debug(f"Token created: {token}")

        return LoginResponse(access_token=token)

    async def register(self, user_register: RegisterUser) -> RegisterResponse:
        if not isEmail(user_register.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email inválido"
            )

        validated_email = user_register.email

        hashed_password = hash_password(user_register.password.strip())
        user_folder = UserFolder()

        existing_user = await self._user_service.get_user_by_email(validated_email)

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

        user_db: User = await self._user_service.create_user(user)

        dest_folder = path.join(
            ".",
            Constants.DESTINATION_FOLDER,
            str(user_db.folder.id if user_db.folder else None),
        )

        if not path.exists(dest_folder):
            folder_response: FolderResponse = await self.directory_manager.createFolder(
                dest_folder
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La carpeta ya existe. No se puede crear una nueva.",
            )

        if user.folder is None or user.folder.id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La carpeta no se creó correctamente.",
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

        response = RegisterResponse(folder=folder_response, access_token=token)

        return response

    async def password_recovery_handshake(
        self, recovery_password_user: RecoveryPassword
    ) -> PasswordRecoveryResponse:
        user = None
        try:
            if isEmail(recovery_password_user.identity):
                user = await self._user_service.get_user_by_email(
                    recovery_password_user.identity
                )
            else:
                user = await self._user_service.get_user_by_username(
                    recovery_password_user.identity
                )
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Credenciales inválidas",
                )

            now = datetime.now()

            if not user.otp or not user.exp or user.exp < int(now.timestamp()):
                otp = OTPUtils.generate_otp()
                new_time = now + timedelta(minutes=10)

                await self._user_repository.update_user(
                    user.id, {"otp": otp, "exp": int(new_time.timestamp())}
                )

                email_service = EmailService(user.email, "Recuperación de contraseña")

                await email_service.send_recovery_password_email(str(otp))

            response = PasswordRecoveryResponse(
                message="Código de recuperación enviado al correo electrónico."
            )
            return response
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating user: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Unexpected error")

    async def change_password(
        self, recovery_password_otp: RecoveryPasswordOtp
    ) -> PasswordRecoveryResponse:
        user = await self._user_service.get_user_by_email(recovery_password_otp.email)

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

        await self._user_service.change_password(
            user.email, recovery_password_otp.password
        )

        email_service = EmailService(user.email, "Confirmación de cambio de contraseña")
        await email_service.send_password_changed_email()

        response = PasswordRecoveryResponse(message="Contraseña cambiada exitosamente.")

        return response
