from datetime import timedelta
from bson import ObjectId
from pydantic import ValidationError
from ..brevio.constants.constants import Constants
from ..models.auth import RecoveryPassword, RecoveryPasswordOtp
from ..models.errors import AuthServiceException
from ..models.user import UserFolder
from ..services.user_service import UserService
from ..repositories.user_repository import UserRepository
from ..utils.email_utils import isEmail
from ..models.user.user import User
from ..models.auth.auth import LoginUser
from ..models.auth.auth import RegisterUser
from .token_service import TokenService
from ..services.email_service import EmailService
from fastapi import HTTPException, status
from pymongo.database import Database
from datetime import timedelta, datetime
from ..utils.password_utils import hash_password, verify_password
from os import path
from ..brevio.managers.directory_manager import DirectoryManager
from ..utils.otp_utils import OTPUtils

class AuthService:
    def __init__(self, db: Database, token_service: TokenService):
        self._db = db
        self._user_repository = UserRepository(self._db)
        self._user_service = UserService(self._user_repository)
        self._token_service = token_service
        self.directory_manager = DirectoryManager()

    async def login(self, user_login: LoginUser):
        try:
            user = None
            if isEmail(user_login.identity):
                user = self._user_service.get_user_by_email(
                    user_login.identity)
            else:
                user = self._user_service.get_user_by_username(
                    user_login.identity)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuario no encontrado"
                )
            if not verify_password(user_login.password, user.password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Contraseña incorrecta"
                )

            token = self._token_service.create_access_token({
                "id": str(user.id),
            }, timedelta(hours=1))

            self._token_service.validate_access_token(token)

            return {"username": user.username, "token": token}

        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error en el inicio de sesión: {str(e)}"
            )

    async def register(self, user_register: RegisterUser):
        try:
            hashed_password = hash_password(user_register.password.strip())

            user_folder = UserFolder()

            user = User(
                username=user_register.username,
                email=user_register.email,
                password=hashed_password,
                folder=user_folder
            )

            try:
                user_db: User = self._user_service.create_user(user)
            except ValueError as e:
                raise AuthServiceException(
                    f"User already exists: {user_register.username}")

            folder_response = None
            dest_folder = path.join(
                ".", Constants.DESTINATION_FOLDER, str(user_db.folder.id))

            if not path.exists(dest_folder):
                folder_response = self.directory_manager.createFolder(dest_folder)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La carpeta ya existe. No se puede crear una nueva."
                )

            token = self._token_service.create_access_token({
                "id": str(user_db.id),
            }, timedelta(hours=1))

            email_service = EmailService(
                user_db.email, f"Usuario {user_db.username} registrado en Brevio")
            await email_service.send_register_email()

            return {"folder_dest": folder_response, "token": token}

        except AuthServiceException as e:
            raise HTTPException(
                status_code=400, detail=f"Error al registrar usuario: {str(e)}")
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Error de validación: {str(e)}"
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error inesperado: {str(e)}")
                
    async def password_recovery_handshake(self, recovery_password_user: RecoveryPassword):
        try:
            if isEmail(recovery_password_user.identity):
                user = self._user_service.get_user_by_email(recovery_password_user.identity)
            else:
                user = self._user_service.get_user_by_username(recovery_password_user.identity)

            if not user:
                raise HTTPException(status_code=404, detail="Usuario no encontrado.")

            user_data = user.model_dump() if hasattr(user, "dict") else user
            now = datetime.now()

            if (not user_data.get("otp")) or (not user_data.get("exp")) or (user_data.get("exp") < int(now.timestamp())):
                otp = OTPUtils.generate_otp()
                new_time = now + timedelta(minutes=10)
                update_user = {"otp": otp, "exp": int(new_time.timestamp())}

                self._user_repository.password_recovery_handshake(user.email, update_user)

                email_service = EmailService(user.email, "Recuperación de contraseña")
                await email_service.send_recovery_password_email(otp)

                return {"detail": "Código de recuperación enviado al correo electrónico."}

            return {"detail": "OTP aún válido"}
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error en el proceso de recuperación de contraseña: {str(e)}"
            )

    async def change_password(self, recovery_password_otp: RecoveryPasswordOtp):
        try:
            user = None

            if isEmail(recovery_password_otp.email):
                user = self._user_service.get_user_by_email(
                    recovery_password_otp.email)

            if not user:
                raise HTTPException(
                    status_code=404, detail="Usuario no existe")

            if user.exp < int(datetime.now().timestamp()):
                raise HTTPException(
                    status_code=400, detail="El código de recuperación ha expirado.")

            if user.otp != recovery_password_otp.otp:
                raise HTTPException(
                    status_code=400, detail="El código de recuperación es incorrecto.")

            await self._user_service.change_password(
                user.email, recovery_password_otp.password)

            email_service = EmailService(
                user.email, "Confirmación de cambio de contraseña")
            await email_service.send_password_changed_email()

            return {"detail": "Contraseña cambiada exitosamente."}

        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error al cambiar la contraseña: {str(e)}"
            )
