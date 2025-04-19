import asyncio
import logging
from pathlib import Path as FilePath
from typing import Any, Dict, List, Tuple

from bson import ObjectId
from fastapi import HTTPException, status

from core.brevio.__main__ import Main
from core.brevio.constants.constants import Constants
from core.brevio.enums.language import LanguageType
from core.brevio.managers.directory_manager import DirectoryManager
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio_api.core.database import DB
from core.brevio_api.models.brevio.brevio_generate import BrevioGenerate, MediaEntry
from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository
from core.brevio_api.repositories.user_repository import UserRepository
from core.brevio_api.services.user_service import UserService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class BrevioService:
    def __init__(self) -> None:
        self._db = DB()
        user_repository = UserRepository(self._db.database())
        entry_repository = FolderEntryRepository(self._db.database())
        self._user_service = UserService(user_repository, entry_repository)
        self.directory_manager = DirectoryManager()
        self._main = Main()

    async def count_media_in_yt_playlist(self, url: str) -> int:
        return await self._main.count_media_in_yt_playlist(url)

    async def get_total_duration(self, url: str) -> int:
        duration_data = await self._main.get_media_duration(url)
        if not isinstance(duration_data, dict) or "durations" not in duration_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid duration data format",
            )
        return sum(int(item["duration"]) for item in duration_data["durations"])

    async def get_media_duration(self, url: str) -> Dict[str, Any]:
        try:
            return await self._main.get_media_duration(url)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail="Error retrieving media duration"
            ) from e

    def get_languages(self) -> List[LanguageType]:
        return self._main.get_languages()

    def get_all_category_style_combinations(self) -> Any:
        return self._main.get_all_category_style_combinations()

    def get_models(self) -> List[str]:
        return self._main.get_models()

    async def generate(
        self, data: BrevioGenerate, _current_user_id: ObjectId
    ) -> Dict[str, Any]:
        try:
            folder_entry = self._user_service.create_folder_entry(_current_user_id)

            if folder_entry is None or folder_entry is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create folder entry",
                )
            current_folder_entry_id = folder_entry

            user = self._user_service.get_user_by_id(_current_user_id)

            if user is None or user.folder is None or user.folder.id is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User or user folder not found",
                )
            user_folder_id = user.folder.id

            return await self._main.generate(
                data,
                self._user_service.create_data_result,
                current_folder_entry_id,
                user_folder_id,
                _current_user_id,
            )

        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error during generation: {str(e)}",
            )

    async def generate_summary_media_upload(
        self,
        files_data: List[Tuple[str, bytes]],
        _current_user_id: ObjectId,
        _prompt_config: PromptConfig,
    ) -> Dict[str, Any]:
        folder_entry = self._user_service.create_folder_entry(_current_user_id)
        if folder_entry is None or folder_entry is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create folder entry",
            )
        current_folder_entry_id = folder_entry

        user = self._user_service.get_user_by_id(_current_user_id)
        if user is None or user.folder is None or user.folder.id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or user folder not found",
            )

        user_folder_id = user.folder.id

        uploads_dir = FilePath(
            f"{Constants.DESTINATION_FOLDER}/{user_folder_id}/{current_folder_entry_id}/"
        )
        uploads_dir.mkdir(parents=True, exist_ok=True)

        saved_files: List[MediaEntry] = []

        for index, (filename, file_content) in enumerate(files_data):
            file_path = uploads_dir / str(index) / f"{filename}"
            await self.save_media(file_content, file_path)
            saved_files.append(MediaEntry(path=file_path))

        _data = BrevioGenerate(data=saved_files, prompt_config=_prompt_config)

        result = await self._main.generate(
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

        if folder_entry is None or folder_entry is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create folder entry",
            )

        current_folder_entry_id = folder_entry

        user = self._user_service.get_user_by_id(_current_user_id)

        if user is None or user.folder is None or user.folder.id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or user folder not found",
            )

        user_folder_id = user.folder.id

        uploads_dir = FilePath(
            f"{Constants.DESTINATION_FOLDER}/{user_folder_id}/{current_folder_entry_id}/"
        )

        tasks = [
            self.save_media(content, uploads_dir / str(index) / filename)
            for index, (filename, content) in enumerate(files_data)
        ]

        await asyncio.gather(*tasks)

        saved_files = [
            MediaEntry(path=uploads_dir / str(index) / filename)
            for index, (filename, _) in enumerate(files_data)
        ]

        _data = BrevioGenerate(data=saved_files, prompt_config=_prompt_config)

        return await self._main.generate_summary_documents(
            _data,
            current_folder_entry_id,
            user_folder_id,
            _current_user_id,
            self._user_service.create_data_result,
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
