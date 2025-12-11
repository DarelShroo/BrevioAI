from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.brevio_api.core.database import AsyncDB
from core.brevio_api.dependencies.db_dependency import get_db
from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository
from core.brevio_api.services.folder_entry_service import FolderEntryService


class FolderEntryServiceDependency:
    async def __call__(
        self, db: AsyncIOMotorDatabase = Depends(get_db)
    ) -> FolderEntryService:
        folder_entry_repo = FolderEntryRepository(db.get_collection("entries"))
        return FolderEntryService(folder_entry_repo)


get_folder_entry_service = FolderEntryServiceDependency()
