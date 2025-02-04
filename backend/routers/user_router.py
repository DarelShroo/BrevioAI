from fastapi import APIRouter
class UserRouter:
    def __init__(self):
        self.router = APIRouter(
            prefix="/user",
            tags=["user"]
        )
        self._register_routes()
    
    def _register_routes(self):
        @self.router.post("/")
        async def get_user_profile():
            pass

user_router = UserRouter().router