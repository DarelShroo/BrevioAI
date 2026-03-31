from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository
from core.brevio_api.repositories.user_repository import UserRepository
from core.brevio_api.services.user_service import UserService


class UserServiceDependency:
    async def __call__(self) -> UserService:
        user_repository = UserRepository()
        folder_entry_repository = FolderEntryRepository()
        return UserService(user_repository, folder_entry_repository)
