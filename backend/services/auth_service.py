from datetime import timedelta
import random
from uuid import uuid1
import uuid
from backend.brevio.constants.constants import Constants
from backend.models.user.recovery_password import RecoveryPassword
from backend.models.user.recovery_password_otp import RecoveryPasswordOtp
from backend.models.user.user_folder import UserFolder
from backend.services.user_service import UserService
from backend.utils import otp_utils
from ..repositories.user_repository import UserRepository
from ..utils.email_utils import isEmail
from ..models.user.user import User
from ..models.user.login_user import LoginUser
from ..models.user.register_user import RegisterUser
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

    async def register(self, user_register: RegisterUser):
        hashed_password = hash_password(user_register.password.strip())
        
        user_folder = UserFolder()

        user = User(
            username = user_register.username,
            email = user_register.email,
            password = hashed_password,
            folder = user_folder
        )

        user_db: User = self._user_service.create_user(user)
        folder_response = self.create_folder(folder_id = user_db.folder.id)

        token = self._token_service.create_access_token({
            "id": str(user_db.id),
        }, timedelta(hours=1))

        email_service = EmailService(user_db.email, f"Usuario {user_db.username} registrado en Brevio")
        email_service.send_register_email()

        return {"folder_dest": folder_response, "token": token}

    def create_folder(self, folder_id):
        result = None
        dest_folder = path.join(
                ".", Constants.DESTINATION_FOLDER, str(folder_id))
        while not path.exists(dest_folder):
            result = self.directory_manager.createFolder(dest_folder)
        return result

    async def password_recovery_handshake(self, recovery_password_user: RecoveryPassword):
        user = None

        if isEmail(recovery_password_user.identity):
            user = self._user_service.get_user_by_email(
                recovery_password_user.identity) 
        else:
            user = self._user_service.get_user_by_username(
                recovery_password_user.identity)

        if not user:
            raise HTTPException(
                status_code=404, detail="Usuario no encontrado.")

        now = datetime.now()

        if "otp" not in user or "exp" not in user or user["exp"] < int(now.timestamp()):
            otp = OTPUtils.generate_otp()
            new_time = now + timedelta(minutes=10)

            update_user = {"otp": otp, "exp": int(new_time.timestamp())}

            self._user_repository.password_recovery_handshake(
                user.email, update_user)

            EmailService(
                user.email, "Recuperación de contraseña").send_recovery_password_email(otp)

            return {"detail": "Código de recuperación enviado al correo electrónico."}

        return {"detail": "OTP aún válido"}



    async def change_password(self, recovery_password_otp: RecoveryPasswordOtp):
        user = None

        if isEmail(recovery_password_otp.email):
            user = self._user_service.get_user_by_email(
                recovery_password_otp.email)

        if not user:
            return HTTPException("Usuario no existe")

        if user.exp < int(datetime.now().timestamp()):
            raise HTTPException(
                status_code=400, detail="El código de recuperación ha expirado.")

        if user.otp!= recovery_password_otp.otp:
            raise HTTPException(
                status_code=400, detail="El código de recuperación es incorrecto.")

        self._user_service.change_password(
            user.email, user.password)

        EmailService(
            user.email, "confirmacion password modificado").send_password_changed_email()

        return
