from datetime import timedelta
from passlib.context import CryptContext
from dotenv import load_dotenv
from os import getenv

from pydantic import EmailStr
from repositories.user_repository import UserRepository
from ..utils.email_utils import isEmail
from ..models.user.user import User
from ..models.user.user_login import UserLogin
from ..models.user.user_register import UserRegister

from .token_service import TokenService

class AuthService:
    def __init(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def login(self, identity: str, password):
        user_login: UserLogin = UserLogin(identity, password)
        user: User = None
        if isEmail(user_login.identity):
            user = UserRepository.get_user_by_email(user_login.identity)

        if(not user):
            return 
            
        user_login_hashed_password = self.pwd_context.encrypt(user_login.password)

        if not self.pwd_context.verify(user_login.password, user_login_hashed_password):
            return 
        
        token = TokenService().create_access_token({
            "username": user.username,
            "email": user.email,
        }, timedelta(hours=1))

        return token
    
    def register(self, username: str, email: EmailStr, password):
        user_register: UserRegister = UserRegister(email, username, password)
        existUserEmail: User = UserRepository().get_user_by_email(user_register.email)
        if(existUserEmail):
            return "Ya existe este email"
        existUserName: User = UserRepository().get_user_by_username(user_register.username)
        
        if (existUserName):
            return "Ya existe este nombre de usuario"
            
        user_register_hashed_password = self.pwd_context.encrypt(user_login.password)
        
        #Guardo el usuario en la BD
        
        token = TokenService().create_access_token({
            "username": user.username,
            "email": user.email,
        }, timedelta(hours=1))

        return token



    
    