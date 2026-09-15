from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.brevio_api.dependencies.db_dependency import get_db
from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository
from core.brevio_api.repositories.library_folder_repository import (
    LibraryFolderRepository,
)
from core.brevio_api.services.library_folder_service import LibraryFolderService


class LibraryFolderServiceDependency:
    async def __call__(
        self, db: AsyncIOMotorDatabase = Depends(get_db)
    ) -> LibraryFolderService:
        return LibraryFolderService(
            LibraryFolderRepository(db.get_collection("library_folders")),
            FolderEntryRepository(db.get_collection("entries")),
        )


library_folder_service_dependency = LibraryFolderServiceDependency()
