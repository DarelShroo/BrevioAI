from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.brevio_api.dependencies.db_dependency import get_db
from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository
from core.brevio_api.repositories.user_repository import UserRepository
from core.brevio_api.services.user_service import UserService


class UserServiceDependency:
    async def __call__(self, db: AsyncIOMotorDatabase = Depends(get_db)) -> UserService:
        user_repository = UserRepository(db.get_collection("users"))
        folder_entry_repository = FolderEntryRepository(db.get_collection("entries"))
        return UserService(user_repository, folder_entry_repository)


user_service_dependency = UserServiceDependency()
