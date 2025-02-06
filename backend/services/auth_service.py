from datetime import timedelta
from passlib.context import CryptContext
from ..repositories.user_repository import UserRepository
from ..utils.email_utils import isEmail
from ..models.user.user import User
from ..models.user.login_user import LoginUser
from ..models.user.register_user import RegisterUser
from .token_service import TokenService
from ..services.email_service import EmailService
from fastapi import HTTPException, status
from pymongo.database import Database

class AuthService:
    def __init__(self, db: Database, token_service: TokenService):
        self.db = db
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.user_repository = UserRepository(self.db)
        self.token_service = token_service

    async def login(self, user_login: LoginUser):
        if isEmail(user_login.identity):
            user_db = self.user_repository.get_user_by_email(
                user_login.identity)
        else:
            user_db = self.user_repository.get_user_by_username(
                user_login.identity)

        if not user_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )

        if not self.pwd_context.verify(user_login.password, user_db["password"]):
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

        user_register.password = self.hash_password(user_register.password)
        user_db = self.user_repository.create_user(user_register)

        token = self.token_service.create_access_token({
            "id": str(user_db.inserted_id),
        }, timedelta(hours=1))

        EmailService("cls18drl@gmail.com",
                     f"Usuario {user_register.username} registrado en Brevio").send_email()

        return {"username": user_register.username, "token": token}

    def hash_password(self, password: str):
        return self.pwd_context.hash(password)
