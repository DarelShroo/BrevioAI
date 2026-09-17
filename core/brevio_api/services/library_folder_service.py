from typing import Optional

from bson import ObjectId
from fastapi import status

from core.brevio_api.models.errors.api_codes import ApiErrorCode, CodedHTTPException
from core.brevio_api.models.user.library_folder import LibraryFolder
from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository
from core.brevio_api.repositories.library_folder_repository import (
    LibraryFolderRepository,
)
from core.shared.utils.source_names import NameValidationError, require_editable_name


class LibraryFolderService:
    def __init__(
        self,
        folder_repo: LibraryFolderRepository,
        entry_repo: FolderEntryRepository,
    ) -> None:
        self._folders = folder_repo
        self._entries = entry_repo

    async def _ensure_indexes(self) -> None:
        await self._folders.ensure_indexes()
        await self._entries.ensure_indexes()

    async def create_folder(self, user_id: str, name: str) -> LibraryFolder:
        await self._ensure_indexes()
        cleaned = self._clean_name(name)
        folder = LibraryFolder(
            user_id=ObjectId(user_id),
            name=cleaned,
            name_key=cleaned.casefold(),
        )
        try:
            return await self._folders.create(folder)
        except ValueError as exc:
            if str(exc) == "duplicate":
                raise CodedHTTPException(
                    status.HTTP_409_CONFLICT, ApiErrorCode.FOLDER_NAME_DUPLICATE
                ) from exc
            raise

    async def list_folders(self, user_id: str) -> list[dict]:
        await self._ensure_indexes()
        folders = await self._folders.list_for_user(user_id)
        counts = await self._entries.count_by_library_folders(user_id)
        payload = []
        for folder in folders:
            payload.append(
                {
                    "id": str(folder.id),
                    "name": folder.name,
                    "created_at": folder.created_at,
                    "updated_at": folder.updated_at,
                    "entry_count": counts.get(str(folder.id), 0),
                }
            )
        return payload

    async def unfiled_count(self, user_id: str) -> int:
        counts = await self._entries.count_by_library_folders(user_id)
        return int(counts.get("unfiled", 0))

    async def rename_folder(
        self, user_id: str, folder_id: str, name: str
    ) -> LibraryFolder:
        folder = await self.require_owned_folder(user_id, folder_id)
        cleaned = self._clean_name(name)
        try:
            return await self._folders.rename(
                str(folder.id), user_id, cleaned, cleaned.casefold()
            )
        except ValueError as exc:
            if str(exc) == "duplicate":
                raise CodedHTTPException(
                    status.HTTP_409_CONFLICT, ApiErrorCode.FOLDER_NAME_DUPLICATE
                ) from exc
            raise CodedHTTPException(
                status.HTTP_404_NOT_FOUND, ApiErrorCode.FOLDER_NOT_FOUND
            ) from exc

    async def delete_folder(self, user_id: str, folder_id: str) -> None:
        folder = await self.require_owned_folder(user_id, folder_id)
        await self._entries.clear_library_folder(user_id, str(folder.id))
        deleted = await self._folders.delete(str(folder.id), user_id)
        if not deleted:
            raise CodedHTTPException(
                status.HTTP_404_NOT_FOUND, ApiErrorCode.FOLDER_NOT_FOUND
            )

    async def require_owned_folder(self, user_id: str, folder_id: str) -> LibraryFolder:
        if not ObjectId.is_valid(folder_id):
            raise CodedHTTPException(
                status.HTTP_404_NOT_FOUND, ApiErrorCode.FOLDER_NOT_FOUND
            )
        folder = await self._folders.get_by_id(folder_id)
        if folder is None:
            raise CodedHTTPException(
                status.HTTP_404_NOT_FOUND, ApiErrorCode.FOLDER_NOT_FOUND
            )
        if str(folder.user_id) != str(user_id):
            raise CodedHTTPException(
                status.HTTP_404_NOT_FOUND, ApiErrorCode.FOLDER_NOT_FOUND
            )
        return folder

    async def resolve_optional_folder(
        self, user_id: str, folder_id: Optional[str]
    ) -> Optional[ObjectId]:
        if folder_id is None or str(folder_id).strip() == "":
            return None
        folder = await self.require_owned_folder(user_id, str(folder_id).strip())
        return ObjectId(str(folder.id))

    async def resolve_destination(
        self,
        user_id: str,
        folder_id: Optional[str],
        folder_name: Optional[str],
    ) -> Optional[ObjectId]:
        cleaned_name = (folder_name or "").strip()
        if cleaned_name:
            created = await self.create_folder(user_id, cleaned_name)
            return ObjectId(str(created.id))
        return await self.resolve_optional_folder(user_id, folder_id)

    @staticmethod
    def _clean_name(name: str) -> str:
        try:
            return require_editable_name(
                name,
                code_empty=ApiErrorCode.FOLDER_NAME_INVALID.value,
                code_too_long=ApiErrorCode.FOLDER_NAME_TOO_LONG.value,
            )
        except NameValidationError as exc:
            status_code = (
                status.HTTP_400_BAD_REQUEST
                if exc.code != ApiErrorCode.FOLDER_NAME_TOO_LONG.value
                else status.HTTP_400_BAD_REQUEST
            )
            raise CodedHTTPException(status_code, exc.code) from exc
