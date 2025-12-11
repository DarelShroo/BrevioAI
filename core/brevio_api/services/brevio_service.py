import asyncio
import io
import json
import logging
import os
import subprocess
import zipfile
from pathlib import Path as FilePath
from typing import Any, Dict, List, Tuple

import aiofiles
from fastapi import HTTPException, status
from fastapi.responses import Response
from pydantic import HttpUrl, ValidationError

from core.brevio.__main__ import Main
from core.brevio.constants.constants import Constants
from core.brevio.managers.directory_manager import DirectoryManager
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio_api.core.database import AsyncDB
from core.brevio_api.models.brevio.file_metadata import FileMetadata
from core.brevio_api.models.brevio.responses.file_listing_response import (
    FileItem,
    FolderContentResponse,
    UserFoldersResponse,
)
from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository
from core.brevio_api.repositories.user_repository import UserRepository
from core.brevio_api.services.billing.billing_estimator_service import (
    BillingEstimatorService,
)
from core.brevio_api.services.billing.usage_cost_tracker import UsageCostTracker
from core.brevio_api.services.user_service import UserService
from core.shared.models.brevio.brevio_generate import BrevioGenerate, MediaEntry

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
        self._db = AsyncDB()
        self._user_service: UserService | None = None
        self.directory_manager = DirectoryManager()
        self._main = Main()
        self._billing_estimator_cost_service = BillingEstimatorService()

    async def init_services(self) -> None:
        await self._db.verify_connection()
        db = self._db.database()
        user_repository = UserRepository(db.get_collection("users"))
        entry_repository = FolderEntryRepository(db.get_collection("entries"))
        self._user_service = UserService(user_repository, entry_repository)

    async def _get_user_service(self) -> UserService:
        if self._user_service is None:
            await self.init_services()
        assert self._user_service is not None
        return self._user_service

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

    async def get_video_info(self, url: HttpUrl) -> List[Dict[str, Any]]:
        return await self._main.get_video_info(url)

    def get_languages(self) -> Any:
        return self._main.get_languages()

    async def get_all_category_style_combinations(self) -> Any:
        return await self._main.get_all_category_style_combinations()

    def get_all_summary_levels(self) -> Any:
        return self._main.get_all_summary_levels()

    def get_all_formats(self) -> Any:
        return self._main.get_all_formats()

    def get_models(self) -> List[str]:
        return self._main.get_models()

    async def generate(
        self,
        data: BrevioGenerate,
        _current_user_id: str,
        _usage_cost_tracker: UsageCostTracker,
    ) -> Dict[str, Any]:
        try:
            await self.init_services()

            assert self._user_service is not None

            entry_name = "Untitled Generation"
            if data.data and data.data[0].url:
                entry_name = str(data.data[0].url)

            folder_entry = await self._user_service.create_folder_entry(
                _current_user_id, name=entry_name
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
                str(user_folder_id),
                _current_user_id,
                _usage_cost_tracker,
            )

            # Scan and update metadata
            entry_dir = FilePath(
                f"{Constants.DESTINATION_FOLDER}/{user_folder_id}/{current_folder_entry_id}/"
            )
            files_metadata = self._scan_directory_metadata(entry_dir, entry_dir)
            await self._user_service.update_folder_entry_metadata(
                current_folder_entry_id, files_metadata
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
        file_paths: List[str],
        _current_user_id: str,
        _prompt_config: PromptConfig,
        _usage_cost_tracker: UsageCostTracker,
    ) -> Dict[str, Any]:
        user_service = await self._get_user_service()

        folder_entry = await user_service.create_folder_entry(_current_user_id)

        if folder_entry is None:
            logger.error("Failed to create folder entry")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create folder entry",
            )
        current_folder_entry_id = folder_entry

        user = await user_service.get_user_by_id(_current_user_id)

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

        import shutil

        for index, src_path in enumerate(file_paths):
            filename = os.path.basename(src_path)
            # Remove UUID prefix if present (simple split by first underscore if we want original name,
            # but maybe keeping unique name is fine. Let's keep unique name to avoid collisions)
            # Actually, the router added a UUID prefix. Let's keep it.

            dest_dir = uploads_dir / str(index)
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / filename

            try:
                shutil.copy2(src_path, dest_path)
                os.chmod(dest_dir, 0o755)
            except Exception as e:
                logger.error(f"Error moving file {src_path} to {dest_path}: {e}")
                raise HTTPException(
                    status_code=500, detail=f"Error processing file {filename}"
                )

        # No need for async gather of save_media anymore

        for index, src_path in enumerate(file_paths):
            filename = os.path.basename(src_path)
            dest_path = uploads_dir / str(index) / filename
            if not await wait_for_file(dest_path):
                logger.error(f"File {dest_path} not created after saving")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"File {dest_path} not created after saving",
                )
            try:
                minutes = await self.count_minutes_media(dest_path)
                total_media_minutes += minutes
                saved_files.append(MediaEntry(path=dest_path))
            except ValidationError as e:
                logger.error(
                    f"Validation error for MediaEntry at {dest_path}: {str(e)}"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Invalid media entry for {dest_path}: {str(e)}",
                )

        _data = BrevioGenerate(data=saved_files, prompt_config=_prompt_config)
        _usage_cost_tracker.add_media_minutes_cost(total_media_minutes)

        logger.info(f"Generating summary for media upload for user {_current_user_id}")
        result = await self._main.generate(
            _data,
            user_service.create_data_result,
            current_folder_entry_id,
            str(user_folder_id),
            _current_user_id,
            _usage_cost_tracker,
        )

        if not isinstance(result, dict):
            logger.error("Unexpected response format from brevio service")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected response format from brevio service",
            )

        # Scan and update metadata
        entry_dir = FilePath(
            f"{Constants.DESTINATION_FOLDER}/{user_folder_id}/{current_folder_entry_id}/"
        )
        files_metadata = self._scan_directory_metadata(entry_dir, entry_dir)
        await user_service.update_folder_entry_metadata(
            current_folder_entry_id, files_metadata
        )

        return result

    async def generate_summary_documents(
        self,
        file_paths: List[str],
        _current_user_id: str,
        _prompt_config: PromptConfig,
        _usage_cost_tracker: UsageCostTracker,
    ) -> Dict[str, str]:
        user_service = await self._get_user_service()

        entry_name = (
            os.path.basename(file_paths[0]) if file_paths else "Untitled Folder"
        )
        folder_entry = await user_service.create_folder_entry(
            _current_user_id, name=entry_name
        )

        if folder_entry is None:
            logger.error("Failed to create folder entry")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create folder entry",
            )

        current_folder_entry_id = folder_entry

        user = await user_service.get_user_by_id(_current_user_id)

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

        import shutil

        for index, src_path in enumerate(file_paths):
            filename = os.path.basename(src_path)
            dest_dir = uploads_dir / str(index)
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / filename

            try:
                shutil.copy2(src_path, dest_path)
            except Exception as e:
                logger.error(f"Error moving file {src_path} to {dest_path}: {e}")
                raise HTTPException(
                    status_code=500, detail=f"Error processing file {filename}"
                )

        saved_files: List[MediaEntry] = []
        for index, src_path in enumerate(file_paths):
            filename = os.path.basename(src_path)
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
            str(user_folder_id),
            _current_user_id,
            user_service.create_data_result,
            _usage_cost_tracker,
        )

        # Scan and update metadata
        entry_dir = FilePath(
            f"{Constants.DESTINATION_FOLDER}/{user_folder_id}/{current_folder_entry_id}/"
        )
        files_metadata = self._scan_directory_metadata(entry_dir, entry_dir)
        await user_service.update_folder_entry_metadata(
            current_folder_entry_id, files_metadata
        )

        return result

    async def save_media(self, content: bytes, file_path: FilePath) -> None:
        try:
            logger.debug(f"Saving media to {file_path}")
            file_path.parent.mkdir(parents=True, exist_ok=True)

            os.chmod(file_path.parent, 0o755)

            await self._write_file(file_path, content)
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

            # Ejecutar el subprocess de forma asíncrona
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise RuntimeError(
                    f"ffprobe falló en {file_path}: {stderr.decode().strip()}"
                )

            probe_data = json.loads(stdout.decode())
            duration_seconds = float(probe_data["format"]["duration"])
            duration_minutes = duration_seconds / 60
            return round(duration_minutes, 2)

        except (KeyError, ValueError, json.JSONDecodeError) as e:
            raise RuntimeError(
                f"Error al obtener la duración de {file_path}: {str(e)}"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Error inesperado al calcular duración de {file_path}: {str(e)}"
            ) from e

    async def _write_file(self, file_path: FilePath, content: bytes) -> None:
        try:
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(content)
                await f.flush()

                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, os.fsync, f.fileno())
        except Exception as e:
            raise RuntimeError(f"Error al escribir en {file_path}: {str(e)}") from e

    def _get_new_filename(
        self,
        original_filename: str,
        rename_map: Dict[str, str],
        strategy: str,
    ) -> str:
        # 1. Check specific rename map
        if original_filename in rename_map:
            return rename_map[original_filename]

        # 2. Apply strategy
        if strategy == "strip_uuid":
            # Assuming format: uuid_rest_of_name.ext
            parts = original_filename.split("_", 1)
            if len(parts) > 1:
                # Check if first part looks like UUID (simple length check or regex if needed)
                # UUIDs are 36 chars.
                if len(parts[0]) == 36:
                    return parts[1]

        # 3. Keep original
        return original_filename

    async def download_files_advanced(
        self, user_id: str, request_data: Any
    ) -> Response:
        from core.brevio_api.models.brevio.requests.download_request import (
            DownloadRequest,
        )

        request: DownloadRequest = request_data

        user_service = await self._get_user_service()
        user = await user_service.get_user_by_id(user_id)

        if user is None or user.folder is None or user.folder.id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or user folder not found",
            )

        user_folder_id = user.folder.id
        target_dir = FilePath(
            f"{Constants.DESTINATION_FOLDER}/{user_folder_id}/{request.folder_id}/"
        )

        if not target_dir.exists() or not target_dir.is_dir():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Folder {request.folder_id} not found for user",
            )

        # Gather all potential files
        all_files = []
        for root, _, filenames in os.walk(target_dir):
            for filename in filenames:
                all_files.append(os.path.join(root, filename))

        files_to_zip: List[Tuple[FilePath, str]] = []  # (path, arcname)

        # Maps for exact relative path matching (highest priority)
        # e.g. "0/summary.pdf" -> "new_name.pdf"
        rename_map_relative = {
            f.filename: f.new_filename
            for f in request.files
            if f.new_filename and (os.sep in f.filename or "/" in f.filename)
        }
        explicit_files_relative = {
            f.filename
            for f in request.files
            if (os.sep in f.filename or "/" in f.filename)
        }

        # Maps for basename matching (lower priority, applies to all files with that name)
        # e.g. "summary.pdf" -> "generic_summary.pdf"
        rename_map_basename = {
            f.filename: f.new_filename
            for f in request.files
            if f.new_filename and not (os.sep in f.filename or "/" in f.filename)
        }
        explicit_files_basename = {
            f.filename
            for f in request.files
            if not (os.sep in f.filename or "/" in f.filename)
        }

        # Filter and Process
        for file_path_str in all_files:
            file_path = FilePath(file_path_str)
            filename = file_path.name
            relative_path = str(file_path.relative_to(target_dir))

            # Normalize relative path separators to match user input style if needed?
            # Assuming user sends "0/file.pdf". Windows might be "0\file.pdf".
            # Let's try to match both forward slash and os.sep.

            # Check extension
            ext = filename.split(".")[-1].lower() if "." in filename else ""
            if request.include_types and ext not in [
                t.lower() for t in request.include_types
            ]:
                # If explicit file (relative or basename), include it regardless of type filter?
                # Logic: Explicit wins.
                if (
                    relative_path not in explicit_files_relative
                    and filename not in explicit_files_basename
                ):
                    continue

            should_include = False
            if request.download_all:
                should_include = True
            elif relative_path in explicit_files_relative:
                should_include = True
            elif filename in explicit_files_basename:
                should_include = True

            if should_include:
                # Determine new name
                # Priority 1: Exact relative path match
                if relative_path in rename_map_relative:
                    new_name = rename_map_relative[relative_path]
                # Priority 2: Basename match
                elif filename in rename_map_basename:
                    new_name = rename_map_basename[filename]
                # Priority 3: Global strategy
                else:
                    new_name = self._get_new_filename(
                        filename, {}, request.global_rename_strategy.value
                    )

                files_to_zip.append((file_path, new_name))

        if not files_to_zip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No files found matching criteria",
            )

        # Create Zip
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            seen_names = set()
            for file_path, arcname in files_to_zip:
                # Handle collisions
                final_name = arcname
                counter = 1
                while final_name in seen_names:
                    name_parts = arcname.rsplit(".", 1)
                    if len(name_parts) == 2:
                        final_name = f"{name_parts[0]}_{counter}.{name_parts[1]}"
                    else:
                        final_name = f"{arcname}_{counter}"
                    counter += 1

                seen_names.add(final_name)
                zip_file.write(file_path, final_name)

        zip_buffer.seek(0)

        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=download_{request.folder_id}.zip"
            },
        )

    async def list_user_folders(self, user_id: str) -> UserFoldersResponse:
        user_service = await self._get_user_service()
        user = await user_service.get_user_by_id(user_id)

        if user is None or user.folder is None or user.folder.id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or user folder not found",
            )

        user_folder_id = user.folder.id
        base_dir = FilePath(f"{Constants.DESTINATION_FOLDER}/{user_folder_id}/")

        if not base_dir.exists():
            return UserFoldersResponse(folder_ids=[])

        folder_ids = []
        for entry_dir in base_dir.iterdir():
            if entry_dir.is_dir():
                folder_ids.append(entry_dir.name)

        return UserFoldersResponse(folder_ids=folder_ids)

    async def list_folder_content(
        self, user_id: str, folder_id: str
    ) -> FolderContentResponse:
        user_service = await self._get_user_service()
        user = await user_service.get_user_by_id(user_id)

        if user is None or user.folder is None or user.folder.id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or user folder not found",
            )

        user_folder_id = user.folder.id
        target_dir = FilePath(
            f"{Constants.DESTINATION_FOLDER}/{user_folder_id}/{folder_id}/"
        )

        if not target_dir.exists() or not target_dir.is_dir():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Folder {folder_id} not found",
            )

        grouped_files = []

        # Recursively walk this entry folder
        for root, _, filenames in os.walk(target_dir):
            if not filenames:
                continue

            current_group = []
            for filename in filenames:
                full_path = FilePath(os.path.join(root, filename))
                relative_path = str(full_path.relative_to(target_dir))
                size = full_path.stat().st_size
                ext = filename.split(".")[-1].lower() if "." in filename else ""

                current_group.append(
                    FileItem(filename=filename, path=relative_path, size=size, type=ext)
                )

            if current_group:
                grouped_files.append(current_group)

        return FolderContentResponse(folder_id=folder_id, files=grouped_files)

    def _scan_directory_metadata(
        self, base_path: FilePath, relative_root: FilePath
    ) -> List[FileMetadata]:
        metadata_list: List[FileMetadata] = []
        if not base_path.exists():
            return metadata_list

        for item in base_path.iterdir():
            relative_path = str(item.relative_to(relative_root))
            if item.is_dir():
                children = self._scan_directory_metadata(item, relative_root)
                metadata = FileMetadata(
                    name=item.name,
                    path=relative_path,
                    type="directory",
                    size=0,  # Directories don't have size in this context
                    children=children,
                )
            else:
                metadata = FileMetadata(
                    name=item.name,
                    path=relative_path,
                    type=item.suffix.lstrip(".") if item.suffix else "unknown",
                    size=item.stat().st_size,
                    children=None,
                )
            metadata_list.append(metadata)

        return metadata_list
