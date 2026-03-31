from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository
from core.brevio_api.services.folder_entry_service import FolderEntryService


class FolderEntryServiceDependency:
    async def __call__(self) -> FolderEntryService:
        folder_entry_repo = FolderEntryRepository()
        return FolderEntryService(folder_entry_repo)
