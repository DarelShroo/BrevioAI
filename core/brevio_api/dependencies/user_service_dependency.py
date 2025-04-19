from core.brevio_api.core.database import DB
from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository
from core.brevio_api.repositories.user_repository import UserRepository
from core.brevio_api.services.user_service import UserService


def get_user_service() -> UserService:
    db = DB()
    user_repository = UserRepository(db.database())
    folder_entry_repository = FolderEntryRepository(db.database())
    return UserService(user_repository, folder_entry_repository)
