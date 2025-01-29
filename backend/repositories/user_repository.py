from ..models.user.user_register import UserRegister
from ..models.user.user import User
import pymongo

class UserRepository:

    def get_user_by_id(self, id: str):
        return "user"
    
    def get_user_by_email(self, email: str):
        return "user"
    
    def get_user_by_username(self, username: str):
        return "user"
    
    def create_user(self, user: UserRegister):
         #guardar usuario
        return "usuario"
    