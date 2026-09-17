import hashlib
import hmac
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from os import path
from typing import Optional
from uuid import uuid4

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from core.brevio.constants.constants import Constants
from core.brevio.managers.directory_manager import DirectoryManager
from core.brevio.models.response_model import FolderResponse
from core.brevio_api.models.auth.auth import (
    LoginUser,
    RecoveryPassword,
    RecoveryPasswordOtp,
    RegisterUser,
)
from core.brevio_api.models.responses.auth_response import PasswordRecoveryResponse
from core.brevio_api.models.user.refresh_session import RefreshSession
from core.brevio_api.models.user.user_folder import UserFolder
from core.brevio_api.models.user.user_model import User
from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository
from core.brevio_api.repositories.refresh_session_repository import (
    RefreshSessionRepository,
)
from core.brevio_api.repositories.user_repository import UserRepository
from core.brevio_api.services.email_service import EmailService
from core.brevio_api.services.token_service import TokenService
from core.brevio_api.services.user_service import UserService
from core.brevio_api.utils.email_utils import isEmail
from core.brevio_api.utils.otp_utils import OTPUtils
from core.brevio_api.utils.password_utils import hash_password, verify_password

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthSession:
    access_token: str
    refresh_token: str
    access_max_age: int
    refresh_max_age: int
    folder: Optional[FolderResponse] = None


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(
        self,
        collection: AsyncIOMotorCollection | AsyncIOMotorDatabase,
        token_service: TokenService,
    ):
        self._db = collection
        self._user_repository = UserRepository(self._db.get_collection("users"))
        self._folder_entry_repository = FolderEntryRepository(
            self._db.get_collection("entries")
        )
        self._refresh_sessions = RefreshSessionRepository(
            self._db.get_collection("refresh_sessions")
        )
        self._user_service = UserService(
            self._user_repository, self._folder_entry_repository
        )
        self._token_service = token_service
        self.directory_manager = DirectoryManager()

    async def _issue_session(
        self, user_id: str, folder: Optional[FolderResponse] = None
    ) -> AuthSession:
        family_id = uuid4().hex
        access_token = self._token_service.create_access_token({"id": user_id})
        refresh_token, jti = self._token_service.create_refresh_token(
            user_id, family_id
        )
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=self._token_service.refresh_max_age_seconds
        )
        await self._refresh_sessions.create(
            RefreshSession(
                user_id=ObjectId(user_id),
                jti=jti,
                family_id=family_id,
                token_hash=hash_refresh_token(refresh_token),
                expires_at=expires_at,
            )
        )
        return AuthSession(
            access_token=access_token,
            refresh_token=refresh_token,
            access_max_age=self._token_service.access_max_age_seconds,
            refresh_max_age=self._token_service.refresh_max_age_seconds,
            folder=folder,
        )

    def _session_expired(self, expires_at: datetime) -> bool:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at < datetime.now(timezone.utc)

    async def refresh(self, refresh_token: str) -> AuthSession:
        payload = self._token_service.validate_refresh_token(refresh_token)
        family_id = str(payload["fam"])
        session = await self._refresh_sessions.get_by_family(family_id)
        presented_hash = hash_refresh_token(refresh_token)

        if (
            session is None
            or session.revoked
            or session.jti != str(payload["jti"])
            or not hmac.compare_digest(session.token_hash, presented_hash)
        ):
            if session is not None:
                await self._refresh_sessions.revoke_family(family_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido",
            )

        if self._session_expired(session.expires_at):
            await self._refresh_sessions.revoke_family(family_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expirado",
            )

        user_id = str(payload["id"])
        access_token = self._token_service.create_access_token({"id": user_id})
        new_refresh, new_jti = self._token_service.create_refresh_token(
            user_id, family_id
        )
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=self._token_service.refresh_max_age_seconds
        )
        rotated = await self._refresh_sessions.rotate(
            family_id,
            expected_jti=str(payload["jti"]),
            expected_token_hash=presented_hash,
            jti=new_jti,
            token_hash=hash_refresh_token(new_refresh),
            expires_at=expires_at,
        )
        if rotated is None:
            # Concurrent refresh or reuse — revoke family (theft / race).
            await self._refresh_sessions.revoke_family(family_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido",
            )
        return AuthSession(
            access_token=access_token,
            refresh_token=new_refresh,
            access_max_age=self._token_service.access_max_age_seconds,
            refresh_max_age=self._token_service.refresh_max_age_seconds,
        )

    async def logout(
        self,
        refresh_token: Optional[str],
        *,
        access_token: Optional[str] = None,
    ) -> None:
        from core.brevio_api.services.session_revocation import (
            deny_access_jti,
            deny_user_access,
        )

        if access_token:
            try:
                access_payload = self._token_service.validate_access_token(access_token)
                jti = str(access_payload.get("jti") or "")
                if jti:
                    deny_access_jti(jti)
            except HTTPException:
                pass

        if not refresh_token:
            return
        try:
            payload = self._token_service.validate_refresh_token(refresh_token)
        except HTTPException:
            return
        family_id = str(payload.get("fam") or "")
        user_id = str(payload.get("id") or "")
        if family_id:
            await self._refresh_sessions.revoke_family(family_id)
        # Defense in depth: deny all access tokens for this user until TTL.
        if user_id:
            deny_user_access(user_id)

    async def login(self, user_login: LoginUser) -> AuthSession:
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
            # Same status/message as bad password to avoid account enumeration.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas",
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

        return await self._issue_session(str(user.id))

    async def register(self, user_register: RegisterUser) -> AuthSession:
        if not isEmail(user_register.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email inválido"
            )

        validated_email = user_register.email

        hashed_password = hash_password(user_register.password.strip())
        user_folder = UserFolder()

        existing_user = await self._user_service.get_user_by_email(validated_email)
        existing_username = await self._user_service.get_user_by_username(
            user_register.username
        )

        if existing_user or existing_username:
            # Generic message — do not reveal which field collided.
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to register with the provided credentials",
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

        email_service = EmailService(
            user_db.email, f"Usuario {user_db.username} registrado en Brevio"
        )

        try:
            await email_service.send_register_email()
        except Exception as e:
            logger.error(f"Failed to send welcome email: {e}")

        return await self._issue_session(str(user.id), folder=folder_response)

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
                # Always return a success-shaped message to avoid email enumeration.
                return PasswordRecoveryResponse(
                    message="Si la cuenta existe, se ha enviado un código de recuperación."
                )

            now = datetime.now()

            if not user.otp or not user.exp or user.exp < int(now.timestamp()):
                otp = OTPUtils.generate_otp()
                new_time = now + timedelta(minutes=10)

                await self._user_repository.update_user(
                    user.id, {"otp": otp, "exp": int(new_time.timestamp()), "otp_attempts": 0}
                )

                email_service = EmailService(user.email, "Recuperación de contraseña")

                await email_service.send_recovery_password_email(str(otp))

            response = PasswordRecoveryResponse(
                message="Si la cuenta existe, se ha enviado un código de recuperación."
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
        from core.shared.utils.environment import env_int

        user = await self._user_service.get_user_by_email(recovery_password_otp.email)

        if not user:
            raise HTTPException(
                status_code=400, detail="Código de recuperación inválido o expirado."
            )

        if not user.exp or user.exp < int(datetime.now().timestamp()):
            raise HTTPException(
                status_code=400, detail="Código de recuperación inválido o expirado."
            )

        max_attempts = max(3, env_int("OTP_MAX_ATTEMPTS", 5))
        attempts = int(getattr(user, "otp_attempts", 0) or 0)
        if attempts >= max_attempts:
            raise HTTPException(
                status_code=400, detail="Código de recuperación inválido o expirado."
            )

        if not OTPUtils.constant_time_equals(user.otp, recovery_password_otp.otp):
            await self._user_repository.update_user(
                user.id, {"otp_attempts": attempts + 1}
            )
            raise HTTPException(
                status_code=400, detail="Código de recuperación inválido o expirado."
            )

        await self._user_service.change_password(
            user.email, recovery_password_otp.password
        )
        await self._refresh_sessions.revoke_all_for_user(user.id)
        from core.brevio_api.services.session_revocation import deny_user_access

        deny_user_access(str(user.id))

        email_service = EmailService(user.email, "Confirmación de cambio de contraseña")
        try:
            await email_service.send_password_changed_email()
        except Exception as e:
            logger.error(f"Failed to send password changed email: {e}")

        response = PasswordRecoveryResponse(message="Contraseña cambiada exitosamente.")

        return response
