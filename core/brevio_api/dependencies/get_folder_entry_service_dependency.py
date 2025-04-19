from core.brevio_api.core.database import DB
from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository
from core.brevio_api.services.folder_entry_service import FolderEntryService


def get_folder_entry_service() -> FolderEntryService:
    db = DB()
    folder_entry_repo = FolderEntryRepository(db.database())
    return FolderEntryService(folder_entry_repo)
