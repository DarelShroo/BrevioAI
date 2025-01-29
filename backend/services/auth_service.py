from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordBearer
import jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
from os import getenv
from repositories.user_repository import UserRepository
from ..utils.email_utils import isEmail
from ..models.user.user import User
from ..models.user.user_login import UserLogin
class AuthService:
    def __init(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
        self.algorithm = getenv("ALGORITHM")
        self.secret_key = getenv("SECRET_KEY")

    def create_access_token(self, data: dict, expires_delta: timedelta | None = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def validate_access_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expirado")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Token inválido")
    
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
        
        #refresh token

        return "token"



    
    