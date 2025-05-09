import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path as FilePath
from typing import Any, Dict, List, Tuple

from bson import ObjectId
from fastapi import HTTPException, status
from pydantic import HttpUrl, ValidationError

from core.brevio.__main__ import Main
from core.brevio.constants.constants import Constants
from core.brevio.managers.directory_manager import DirectoryManager
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio_api.core.database import DB
from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository
from core.brevio_api.repositories.user_repository import UserRepository
from core.brevio_api.services.billing.billing_estimator_service import (
    BillingEstimatorService,
)
from core.brevio_api.services.billing.usage_cost_tracker import UsageCostTracker
from core.brevio_api.services.user_service import UserService
from core.shared.models.brevio.brevio_generate import BrevioGenerate, MediaEntry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


async def wait_for_file(
    file_path: FilePath, max_attempts: int = 10, delay: float = 0.1
) -> bool:
    loop = asyncio.get_running_loop()
    for attempt in range(max_attempts):
        exists = await loop.run_in_executor(None, os.path.exists, file_path)
        if exists:
            logger.debug(
                f"File confirmed to exist at {file_path} after {attempt + 1} attempts"
            )
            return True
        logger.debug(
            f"File not found at {file_path}, attempt {attempt + 1}/{max_attempts}"
        )
        await asyncio.sleep(delay)
    logger.error(f"File {file_path} not found after {max_attempts} attempts")
    return False


class BrevioService:
    def __init__(self) -> None:
        self._db = DB()
        user_repository = UserRepository(self._db.database())
        entry_repository = FolderEntryRepository(self._db.database())
        self._user_service = UserService(user_repository, entry_repository)
        self.directory_manager = DirectoryManager()
        self._main = Main()
        self._billing_estimator_cost_service = BillingEstimatorService()

    async def count_media_in_yt_playlist(self, url: HttpUrl) -> int:
        return await self._main.count_media_in_yt_playlist(url)

    async def get_total_duration(self, url: HttpUrl) -> float:
        duration_data = await self._main.get_media_duration(url)

        if not isinstance(duration_data, dict) or "durations" not in duration_data:
            logger.error("Invalid duration data format")
            raise ValueError("Invalid duration data format")

        return sum(int(item["duration"]) for item in duration_data["durations"])

    async def get_media_duration(self, url: HttpUrl) -> Dict[str, Any]:
        try:
            return await self._main.get_media_duration(url)
        except Exception as e:
            logger.error(f"Error retrieving media duration for {url}: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Error retrieving media duration"
            ) from e

    def get_languages(self) -> List[str]:
        return self._main.get_languages()

    def get_all_category_style_combinations(self) -> Any:
        return self._main.get_all_category_style_combinations()

    def get_models(self) -> List[str]:
        return self._main.get_models()

    async def generate(
        self,
        data: BrevioGenerate,
        _current_user_id: ObjectId,
        _usage_cost_tracker: UsageCostTracker,
    ) -> Dict[str, Any]:
        try:
            folder_entry = await self._user_service.create_folder_entry(
                _current_user_id
            )

            if folder_entry is None:
                logger.error("Failed to create folder entry")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create folder entry",
                )
            current_folder_entry_id = folder_entry

            user = await self._user_service.get_user_by_id(_current_user_id)

            if user is None or user.folder is None or user.folder.id is None:
                logger.error("User or user folder not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User or user folder not found",
                )
            user_folder_id = user.folder.id

            total_cost_media_minutes = 0.0

            for media in data.data:
                if media.url:
                    duration = await self.get_total_duration(media.url)
                    total_cost_media_minutes += (
                        duration / 60
                    )  # Convertir segundos a minutos
                else:
                    logger.error("Media URL is required")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Media URL is required",
                    )

            _usage_cost_tracker.add_media_minutes_cost(total_cost_media_minutes)

            logger.info(f"Generating content for user {_current_user_id}")
            result = await self._main.generate(
                data,
                self._user_service.create_data_result,
                current_folder_entry_id,
                user_folder_id,
                _current_user_id,
                _usage_cost_tracker,
            )
            return result

        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Unexpected error during generation: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error during generation: {str(e)}",
            )

    async def generate_summary_media_upload(
        self,
        files_data: List[Tuple[str, bytes]],
        _current_user_id: ObjectId,
        _prompt_config: PromptConfig,
        _usage_cost_tracker: UsageCostTracker,
    ) -> Dict[str, Any]:
        folder_entry = await self._user_service.create_folder_entry(_current_user_id)

        if folder_entry is None:
            logger.error("Failed to create folder entry")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create folder entry",
            )
        current_folder_entry_id = folder_entry

        user = await self._user_service.get_user_by_id(_current_user_id)

        if user is None or user.folder is None or user.folder.id is None:
            logger.error("User or user folder not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or user folder not found",
            )

        user_folder_id = user.folder.id

        uploads_dir = FilePath(
            f"{Constants.DESTINATION_FOLDER}/{user_folder_id}/{current_folder_entry_id}/"
        )

        saved_files: List[MediaEntry] = []
        total_media_minutes = 0.0

        tasks = [
            self.save_media(content, uploads_dir / str(index) / filename)
            for index, (filename, content) in enumerate(files_data)
        ]
        await asyncio.gather(*tasks)

        for index, (filename, _) in enumerate(files_data):
            file_path = uploads_dir / str(index) / f"{filename}"
            if not await wait_for_file(file_path):
                logger.error(f"File {file_path} not created after saving")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"File {file_path} not created after saving",
                )
            try:
                minutes = await self.count_minutes_media(file_path)
                total_media_minutes += minutes
                saved_files.append(MediaEntry(path=file_path))
            except ValidationError as e:
                logger.error(
                    f"Validation error for MediaEntry at {file_path}: {str(e)}"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Invalid media entry for {file_path}: {str(e)}",
                )

        _data = BrevioGenerate(data=saved_files, prompt_config=_prompt_config)
        _usage_cost_tracker.add_media_minutes_cost(total_media_minutes)

        logger.info(f"Generating summary for media upload for user {_current_user_id}")
        result = await self._main.generate(
            _data,
            self._user_service.create_data_result,
            current_folder_entry_id,
            user_folder_id,
            _current_user_id,
            _usage_cost_tracker,
        )

        if not isinstance(result, dict):
            logger.error("Unexpected response format from brevio service")
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
        _usage_cost_tracker: UsageCostTracker,
    ) -> Dict[str, str]:
        folder_entry = await self._user_service.create_folder_entry(_current_user_id)

        if folder_entry is None:
            logger.error("Failed to create folder entry")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create folder entry",
            )

        current_folder_entry_id = folder_entry

        user = await self._user_service.get_user_by_id(_current_user_id)

        if user is None or user.folder is None or user.folder.id is None:
            logger.error("User or user folder not found")
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

        saved_files: List[MediaEntry] = []
        for index, (filename, _) in enumerate(files_data):
            file_path = uploads_dir / str(index) / filename
            if not await wait_for_file(file_path):
                logger.error(f"File {file_path} not created after saving")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"File {file_path} not created after saving",
                )
            try:
                saved_files.append(MediaEntry(path=file_path))
            except ValidationError as e:
                logger.error(
                    f"Validation error for MediaEntry at {file_path}: {str(e)}"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Invalid media entry for {file_path}: {str(e)}",
                )

        _data = BrevioGenerate(data=saved_files, prompt_config=_prompt_config)

        logger.info(f"Generating summary documents for user {_current_user_id}")
        result = await self._main.generate_summary_documents(
            _data,
            current_folder_entry_id,
            user_folder_id,
            _current_user_id,
            self._user_service.create_data_result,
            _usage_cost_tracker,
        )
        return result

    async def save_media(self, content: bytes, file_path: FilePath) -> None:
        try:
            logger.debug(f"Saving media to {file_path}")
            file_path.parent.mkdir(parents=True, exist_ok=True)

            os.chmod(file_path.parent, 0o755)

            await asyncio.to_thread(self._write_file, file_path, content)
            logger.debug(f"Successfully saved media to {file_path}")
        except Exception as e:
            logger.error(
                f"Error saving media file {file_path}: {str(e)}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error saving media file {file_path}: {str(e)}",
            )

    async def count_minutes_media(self, file_path: FilePath) -> float:
        try:
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                str(file_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            probe_data = json.loads(result.stdout)

            duration_str = probe_data["format"]["duration"]
            duration_seconds = float(duration_str)
            duration_minutes = duration_seconds / 60
            return round(duration_minutes, 2)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Error al ejecutar ffprobe en {file_path}: {e.stderr}"
            ) from e
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            raise RuntimeError(
                f"Error al obtener la duración de {file_path}: {str(e)}"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Error inesperado al calcular duración de {file_path}: {str(e)}"
            ) from e

    def _write_file(self, file_path: FilePath, content: bytes) -> None:
        with open(file_path, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
