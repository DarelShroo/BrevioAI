from fastapi import APIRouter
from ..models.user.login_user import LoginUser
from ..models.user.register_user import RegisterUser
from ..services.auth_service import AuthService
class AuthRoutes:
    def __init__(self):
        self.router = APIRouter(
            prefix="/auth",
            tags=["authentication"]
        )
        self._register_routes()

    def _register_routes(self):
        @self.router.post("/login")
        async def login(login_user: LoginUser):
            try: 
                return AuthService().login(login_user)
            except Exception as e:
                raise e


        @self.router.post("/register")
        async def register(user_register: RegisterUser):
            try: 
                return AuthService().register(user_register)
            except Exception as e:
                raise e
            
        
auth_router = AuthRoutes().router