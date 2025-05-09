import logging
from http.client import InvalidURL
from typing import List

from bson import ObjectId
from fastapi import HTTPException

from core.brevio_api.models.user.folder_entry import FolderEntry
from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class FolderEntryService:
    def __init__(self, folder_entry_repo: FolderEntryRepository):
        self._folder_entry_repo = folder_entry_repo

    async def get_entries(
        self, _user_id: ObjectId, _entries_refs: List[str]
    ) -> List[FolderEntry]:
        _entries_refs_obj_ids = []
        try:
            for entry_id in _entries_refs:
                try:
                    _entries_refs_obj_ids.append(ObjectId(entry_id))
                except (TypeError, InvalidURL):
                    raise HTTPException(
                        status_code=400, detail=f"Invalid ObjectId format: {entry_id}"
                    )

            user_entries = await self._folder_entry_repo.get_entries_ids_by_user_id(
                _user_id, _entries_refs_obj_ids
            )

            if not user_entries:
                raise HTTPException(status_code=404, detail="No Entries found")

            return user_entries
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving user entries: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error retrieving user entries")
