import logging
from datetime import datetime, timezone
from http.client import InvalidURL
from typing import List, Optional

from bson import ObjectId
from fastapi import HTTPException

from core.brevio_api.models.user.folder_entry import FolderEntry
from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository
from core.shared.utils.source_names import resolve_entry_display_name

logger = logging.getLogger(__name__)


class FolderEntryService:
    def __init__(self, folder_entry_repo: FolderEntryRepository):
        self._folder_entry_repo = folder_entry_repo

    async def _ensure_independent_name(self, entry: FolderEntry) -> FolderEntry:
        resolved = resolve_entry_display_name(
            entry_id=str(entry.id) if entry.id is not None else None,
            name=entry.name,
            original_name=entry.original_name,
            results=entry.results,
        )
        if resolved == (entry.name or "").strip():
            return entry
        try:
            return await self._folder_entry_repo.update_folder_entry(
                str(entry.id),
                {
                    "$set": {
                        "name": resolved,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
        except Exception:
            logger.warning(
                "Failed to backfill independent name for entry %s",
                entry.id,
                exc_info=True,
            )
            entry.name = resolved
            return entry

    async def _normalize_entries(self, entries: List[FolderEntry]) -> List[FolderEntry]:
        normalized: List[FolderEntry] = []
        for entry in entries:
            normalized.append(await self._ensure_independent_name(entry))
        return normalized

    async def get_entries(
        self, _user_id: str, _entries_refs: List[str]
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

            return await self._normalize_entries(user_entries)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving user entries: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error retrieving user entries")

    async def list_entries_for_user(
        self, user_id: str, folder_id: Optional[str] = None
    ) -> List[FolderEntry]:
        try:
            entries = await self._folder_entry_repo.get_entries_by_user(
                user_id, library_folder_id=folder_id
            )
            return await self._normalize_entries(entries)
        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(
                f"Error listing entries for user {user_id}: {str(e)}", exc_info=True
            )
            raise HTTPException(status_code=500, detail="Error retrieving user entries")
