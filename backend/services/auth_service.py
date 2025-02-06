from datetime import timedelta
import random
from backend.models.user.recovery_password import RecoveryPassword
from backend.models.user.recovery_password_otp import RecoveryPasswordOtp
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

class AuthService:
    def __init__(self, db: Database, token_service: TokenService):
        self.db = db
        self.user_repository = UserRepository(self.db)
        self.token_service = token_service

    async def login(self, user_login: LoginUser):
        if isEmail(user_login.identity):
            user_db = self.user_repository.get_user_by_email(
                user_login.identity)
        else:
            print("no  es email")
            user_db = self.user_repository.get_user_by_username(
                user_login.identity)

        if not user_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )

        if not verify_password(user_login.password, user_db["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Contraseña incorrecta"
            )

        user_db["_id"] = str(user_db["_id"])
        user = User(**user_db)

        token = self.token_service.create_access_token({
            "id": str(user.id),
        }, timedelta(hours=1))

        self.token_service.validate_access_token(token)

        return {"username": user.username, "token": token}

    async def register(self, user_register: RegisterUser):
        if self.user_repository.get_user_by_email(user_register.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya está registrado"
            )

        if self.user_repository.get_user_by_username(user_register.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre de usuario ya está registrado"
            )

        user_register.password = hash_password(user_register.password)
        user_db: User = self.user_repository.create_user(user_register)
        token = self.token_service.create_access_token({
            "id": str(user_db["_id"]),
        }, timedelta(hours=1))

        EmailService(user_db["email"],
                     f"Usuario {user_register.username} registrado en Brevio").send_register_email()

        return {"username": user_register.username, "token": token}

    async def password_recovery_handshake(self, recovery_password_user: RecoveryPassword):
        user = None

        if isEmail(recovery_password_user.identity):
            user = self.user_repository.get_user_by_email(recovery_password_user.identity)
        else:
            user = self.user_repository.get_user_by_username(recovery_password_user.identity)

        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")

        now = datetime.now()

        if "otp" not in user or "exp" not in user or user["exp"] < int(now.timestamp()):
            otp = self.generate_otp()
            new_time = now + timedelta(minutes=10)

            update_user = {"otp": otp, "exp": int(new_time.timestamp())}
            self.user_repository.password_recovery_handshake(user["email"], update_user)

            EmailService(user["email"], "Recuperación de contraseña").send_recovery_password_email(otp)

            return {"detail": "Código de recuperación enviado al correo electrónico."}

        return {"detail": "OTP aún válido"}


    @staticmethod
    def generate_otp(longitud=6):
        return int(''.join(str(random.randint(0, 9)) for _ in range(longitud)))

    async def change_password(self, recovery_password_otp: RecoveryPasswordOtp):
        user = None

        if isEmail(recovery_password_otp.email):
            user = self.user_repository.get_user_by_email(
                recovery_password_otp.email)

        if not user:
            return HTTPException("Usuario no existe")

        if user["exp"] < int(datetime.now().timestamp()):
            raise HTTPException(
                status_code=400, detail="El código de recuperación ha expirado.")

        if user["otp"] != recovery_password_otp.otp:
            raise HTTPException(
                status_code=400, detail="El código de recuperación es incorrecto.")

        user["password"] = hash_password(recovery_password_otp.password)
        now = int(datetime.now().timestamp())
        self.user_repository.change_password(
            user["email"], user["password"], exp=now - 10000)

        EmailService(
            user["email"], "confirmacion password modificado").send_password_changed_email()

        return
