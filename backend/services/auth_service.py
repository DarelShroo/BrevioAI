from datetime import timedelta
from passlib.hash import bcrypt
from passlib.context import CryptContext
from ..repositories.user_repository import UserRepository
from ..utils.email_utils import isEmail
from ..models.user.user import User
from ..models.user.login_user import LoginUser
from ..models.user.register_user import RegisterUser
from ..utils.db import DB
from .token_service import TokenService
from ..repositories.user_repository import UserRepository


class AuthService:
    def __init__(self):
        self.users_db = DB().database()['users']
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def login(self, user_login: LoginUser):
        user_db: dict = None
        if isEmail(user_login.identity):
            user_db = UserRepository().get_user_by_email(user_login.identity)
        else:
            user_db = UserRepository().get_user_by_username(user_login.identity)

        if (not user_db):
            return "NO existe"

        if not self.pwd_context.verify(user_login.password, user_db["password"]):
            return "password inválido"

        if "_id" in user_db:
            user_db["_id"] = str(user_db["_id"])

        user: User = User(**user_db)

        token = TokenService().create_access_token({
            "id": str(user.id),
        }, timedelta(hours=1))

        return {"username": user.username, "token": token}

    def register(self, user_register: RegisterUser):
        existUserEmail: User = UserRepository().get_user_by_email(user_register.email)
        if (existUserEmail):
            return "Ya existe este email"

        existUserName: User = UserRepository().get_user_by_username(user_register.username)
        if (existUserName):
            return "Ya existe este nombre de usuario"

        user_register.password = self.hash_password(
            user_register.password)

        user_db = UserRepository().create_user(user_register)

        token = TokenService().create_access_token({
            "id": user_db.inserted_id,
        }, timedelta(hours=1))

        return {"username": user_register.username, "token": token}

    def hash_password(self, password: str):
        return self.pwd_context.hash(password)
