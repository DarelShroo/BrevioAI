import asyncio
from pathlib import Path as FilePath
from types import CoroutineType
from typing import Any, Coroutine, Dict, List, Tuple, cast

from bson import ObjectId
from fastapi import HTTPException, status

from backend.brevio.__main__ import Main as Brevio
from backend.brevio.constants.constants import Constants
from backend.brevio.managers import DirectoryManager
from backend.brevio.models import PromptConfig
from backend.core.database import DB
from backend.models.brevio.brevio_generate import BrevioGenerate, MediaEntry
from backend.repositories import UserRepository
from backend.repositories.folder_entry_repository import FolderEntryRepository
from backend.services.user_service import UserService
from brevio.enums.language import LanguageType


class BrevioService:
    def __init__(self) -> None:
        self._db = DB()
        user_repository = UserRepository(self._db.database())
        entry_repository = FolderEntryRepository(self._db.database())
        self._user_service = UserService(user_repository, entry_repository)
        self.directory_manager = DirectoryManager()
        self._brevio = Brevio()

    async def count_media_in_yt_playlist(self, url: str) -> int:
        return await self._brevio.count_media_in_yt_playlist(url)

    async def get_total_duration(self, url: str) -> int:
        duration_data = await self._brevio.get_media_duration(url)
        if not isinstance(duration_data, dict) or "durations" not in duration_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid duration data format",
            )
        return sum(int(item["duration"]) for item in duration_data["durations"])

    async def get_media_duration(self, url: str) -> Dict[str, Any]:
        try:
            return await self._brevio.get_media_duration(url)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail="Error retrieving media duration"
            ) from e

    def get_languages(self) -> List[LanguageType]:
        return self._brevio.get_languages()

    def get_all_category_style_combinations(self) -> Any:
        return self._brevio.get_all_category_style_combinations()

    def get_models(self) -> List[str]:
        return self._brevio.get_models()

    async def generate(
        self, data: BrevioGenerate, _current_user_id: ObjectId
    ) -> Dict[str, Any]:
        folder_entry = self._user_service.create_folder_entry(_current_user_id)
        if folder_entry is None or folder_entry.id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create folder entry",
            )
        current_folder_entry_id = folder_entry.id

        user = self._user_service.get_user_by_id(_current_user_id)
        if user is None or user.folder is None or user.folder.id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or user folder not found",
            )
        user_folder_id = user.folder.id

        return await self._brevio.generate(
            data,
            self._user_service.create_data_result,
            current_folder_entry_id,
            user_folder_id,
            _current_user_id,
        )

    async def generate_summary_media_upload(
        self,
        files_data: List[Tuple[str, bytes]],
        _current_user_id: ObjectId,
        _prompt_config: PromptConfig,
    ) -> Dict[str, Any]:
        folder_entry = self._user_service.create_folder_entry(_current_user_id)
        if folder_entry is None or folder_entry.id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create folder entry",
            )
        current_folder_entry_id: ObjectId = folder_entry.id

        user = self._user_service.get_user_by_id(_current_user_id)
        if user is None or user.folder is None or user.folder.id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or user folder not found",
            )

        user_folder_id: ObjectId = user.folder.id

        uploads_dir = FilePath(
            f"{Constants.DESTINATION_FOLDER}/{user_folder_id}/{current_folder_entry_id}/"
        )
        uploads_dir.mkdir(parents=True, exist_ok=True)

        saved_files: List[MediaEntry] = []

        tasks: list[CoroutineType] = []
        for index, (filename, file_content) in enumerate(files_data):
            file_path = uploads_dir / str(index) / f"{filename}"
            await self.save_media(file_content, file_path)

            saved_files.append(MediaEntry(path=file_path))

        _data = BrevioGenerate(
            data=saved_files, prompt_config=_prompt_config.model_dump()
        )

        result = await self._brevio.generate(
            _data,
            self._user_service.create_data_result,
            current_folder_entry_id,
            user_folder_id,
            _current_user_id,
        )

        if not isinstance(result, dict):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected response format from brevio service",
            )

        return result

    async def generate_summary_documents(
        self,
        files_data: List[Tuple[str, bytes]],
        _current_user_id: ObjectId,
        _prompt_config: PromptConfig,
    ) -> Dict[str, str]:
        folder_entry = self._user_service.create_folder_entry(_current_user_id)

        if folder_entry is None or folder_entry.id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create folder entry",
            )

        current_folder_entry_id: ObjectId = folder_entry.id

        user = self._user_service.get_user_by_id(_current_user_id)

        if user is None or user.folder is None or user.folder.id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or user folder not found",
            )

        _user_folder_id: ObjectId = user.folder.id

        uploads_dir = FilePath(
            f"{Constants.DESTINATION_FOLDER}/{_user_folder_id}/{current_folder_entry_id}/"
        )

        saved_files: List[MediaEntry] = []
        loop = asyncio.get_event_loop()
        tasks = []

        for index, (filename, file_content) in enumerate(files_data):
            file_path = uploads_dir / str(index) / f"{filename}"
            tasks.append(self.save_media(file_content, file_path))

        await asyncio.gather(*tasks)

        saved_files = [
            MediaEntry(path=uploads_dir / str(index) / filename)
            for index, (filename, _) in enumerate(files_data)
        ]

        _data = BrevioGenerate(
            data=saved_files, prompt_config=_prompt_config.model_dump()
        )

        return await self._brevio.generate_summary_documents(
            _data,
            self._user_service.create_data_result,
            current_folder_entry_id,
            _user_folder_id,
            _current_user_id,
        )

    async def save_media(self, content: bytes, file_path: FilePath) -> None:
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(self._write_file, file_path, content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error saving media file {file_path}: {str(e)}",
            )

    def _write_file(self, file_path: FilePath, content: bytes) -> None:
        with open(file_path, "wb") as f:
            f.write(content)
