import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path as FilePath
from typing import Any, Dict, List, Tuple

import aiofiles
from bson import ObjectId
from fastapi import HTTPException, status
from pydantic import HttpUrl, ValidationError

from core.brevio.__main__ import Main
from core.brevio.constants.constants import Constants
from core.brevio.managers.directory_manager import DirectoryManager
from core.brevio.models.prompt_config_model import PromptConfig
from core.brevio_api.core.database import AsyncDB
from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository
from core.brevio_api.repositories.user_repository import UserRepository
from core.brevio_api.services.user_service import UserService
from core.shared.models.brevio.brevio_generate import BrevioGenerate, MediaEntry
from core.shared.utils.source_names import names_for_batch, originals_for_batch

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

    async def get_user_credits(self, user_id: str) -> float:
        try:
            user_service = await self._get_user_service()
            user = await user_service.get_user_by_id(user_id)
        except HTTPException:
            return 0.0
        if user is None:
            return 0.0
        return float(user.user_credit or 0)

    async def create_summary_job(
        self,
        user_id: str,
        *,
        name: str = "",
        original_name: str | None = None,
        library_folder_id: str | None = None,
        language: str | None = None,
        model: str | None = None,
        category: str | None = None,
        style: str | None = None,
        format: str | None = None,
        summary_level: str | None = None,
        source_type: str | None = None,
    ) -> str:
        user_service = await self._get_user_service()
        return await user_service.create_folder_entry(
            user_id,
            name=name,
            original_name=original_name,
            library_folder_id=library_folder_id,
            language=language,
            model=model,
            category=category,
            style=style,
            format=format,
            summary_level=summary_level,
            source_type=source_type,
        )

    async def _resolve_library_folder(
        self,
        user_id: str,
        folder_id: str | None,
        folder_name: str | None,
    ):
        from core.brevio_api.repositories.library_folder_repository import (
            LibraryFolderRepository,
        )
        from core.brevio_api.services.library_folder_service import LibraryFolderService

        db = self._db.database()
        service = LibraryFolderService(
            LibraryFolderRepository(db.get_collection("library_folders")),
            FolderEntryRepository(db.get_collection("entries")),
        )
        return await service.resolve_destination(user_id, folder_id, folder_name)

    @staticmethod
    def _prompt_metadata(
        prompt_config: PromptConfig, source_type: str
    ) -> dict[str, str]:
        return {
            "language": prompt_config.language.name,
            "model": prompt_config.model.value,
            "category": prompt_config.category,
            "style": prompt_config.style,
            "format": prompt_config.format.value,
            "summary_level": prompt_config.summary_level.value,
            "source_type": source_type,
        }

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
    ) -> Dict[str, Any]:
        try:
            await self.init_services()

            assert self._user_service is not None

            folder_oid = await self._resolve_library_folder(
                _current_user_id, data.library_folder_id, data.folder_name
            )
            sources = [
                str(media.path or media.url or "") for media in (data.data or [])
            ]
            display_name, original_name = names_for_batch(
                sources,
                kind="video",
                entry_name=getattr(data, "name", None),
            )
            if not original_name:
                original_name = originals_for_batch(sources, kind="video")
            folder_entry = await self._user_service.create_folder_entry(
                _current_user_id,
                name=display_name,
                original_name=original_name or None,
                library_folder_id=folder_oid,
                **self._prompt_metadata(data.prompt_config, "youtube"),
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

            logger.info(f"Generating content for user {_current_user_id}")
            try:
                result = await self._main.generate(
                    data,
                    self._user_service.create_data_result,
                    current_folder_entry_id,
                    str(user_folder_id),
                    _current_user_id,
                )
                return result
            except Exception:
                try:
                    await self._user_service.fail_processing_results(
                        current_folder_entry_id,
                        Exception("Summary job terminated without COMPLETED"),
                    )
                except Exception as persist_error:
                    logger.error(
                        "Failed to mark leftover PROCESSING results as FAILED for folder %s: %s",
                        current_folder_entry_id,
                        persist_error,
                        exc_info=True,
                    )
                raise

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
        _current_user_id: str,
        _prompt_config: PromptConfig,
        folder_entry_id: str | None = None,
        transcription_provider: str | None = None,
        transcription_model: str | None = None,
    ) -> Dict[str, Any]:
        user_service = await self._get_user_service()

        meta = self._prompt_metadata(_prompt_config, "media")
        folder_entry = folder_entry_id
        if folder_entry is None:
            folder_entry = await user_service.create_folder_entry(
                _current_user_id, **meta
            )
        else:
            existing_entry = (
                await user_service._folder_entry_repo.get_folder_entry_by_id(
                    folder_entry
                )
            )
            if str(existing_entry.user_id) != str(_current_user_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User does not own the supplied summary job",
                )
            await user_service.update_folder_entry_metadata(folder_entry, **meta)

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

        _data = BrevioGenerate(
            data=saved_files,
            prompt_config=_prompt_config,
            transcription_provider=transcription_provider,
            transcription_model=transcription_model,
        )

        logger.info(f"Generating summary for media upload for user {_current_user_id}")
        try:
            result = await self._main.generate(
                _data,
                user_service.create_data_result,
                current_folder_entry_id,
                str(user_folder_id),
                _current_user_id,
            )
        except Exception:
            try:
                await user_service.fail_processing_results(
                    current_folder_entry_id,
                    Exception("Summary job terminated without COMPLETED"),
                )
            except Exception as persist_error:
                logger.error(
                    "Failed to mark leftover PROCESSING results as FAILED for folder %s: %s",
                    current_folder_entry_id,
                    persist_error,
                    exc_info=True,
                )
            raise

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
        _current_user_id: str,
        _prompt_config: PromptConfig,
        folder_entry_id: str | None = None,
    ) -> Dict[str, str]:
        user_service = await self._get_user_service()

        folder_entry = folder_entry_id
        meta = self._prompt_metadata(_prompt_config, "documents")
        if folder_entry is None:
            folder_entry = await user_service.create_folder_entry(
                _current_user_id, **meta
            )
        else:
            existing_entry = (
                await user_service._folder_entry_repo.get_folder_entry_by_id(
                    folder_entry
                )
            )
            if str(existing_entry.user_id) != str(_current_user_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User does not own the supplied summary job",
                )
            await user_service.update_folder_entry_metadata(folder_entry, **meta)

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
                raise ValueError(
                    f"Invalid media entry for {file_path}: {str(e)}",
                )

        _data = BrevioGenerate(data=saved_files, prompt_config=_prompt_config)

        logger.info(f"Generating summary documents for user {_current_user_id}")
        try:
            result = await self._main.generate_summary_documents(
                _data,
                current_folder_entry_id,
                str(user_folder_id),
                _current_user_id,
                user_service.create_data_result,
            )
            return result
        except Exception:
            try:
                await user_service.fail_processing_results(
                    current_folder_entry_id,
                    Exception("Summary job terminated without COMPLETED"),
                )
            except Exception as persist_error:
                logger.error(
                    "Failed to mark leftover PROCESSING results as FAILED for folder %s: %s",
                    current_folder_entry_id,
                    persist_error,
                    exc_info=True,
                )
            raise

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

    async def download_summary_file(
        self,
        user_id: str,
        folder_entry_id: str,
        requested_format: str,
        result_index: int | None = None,
    ) -> Tuple[str, str, str]:
        """
        Returns (file_path, filename, media_type) for downloading a summary in the requested format.
        Generates .docx or .pdf on the fly if not already generated.
        """
        user_service = await self._get_user_service()

        if not ObjectId.is_valid(folder_entry_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid folder entry ID format",
            )

        folder_entry = await user_service._folder_entry_repo.get_folder_entry_by_id(
            folder_entry_id
        )
        if not folder_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"FolderEntry with ID {folder_entry_id} not found",
            )

        if str(folder_entry.user_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have access to this folder entry",
            )

        if not folder_entry.results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No results found in folder entry",
            )

        if result_index is None:
            if len(folder_entry.results) == 1:
                result_index = 0
            else:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "result_index is required when the entry has multiple results"
                    ),
                )

        if result_index < 0 or result_index >= len(folder_entry.results):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Result index {result_index} not found in folder entry",
            )

        result_item = folder_entry.results[result_index]
        if not result_item.is_completed():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Summary is not completed and cannot be downloaded "
                    f"(status={result_item.status or 'unknown'}, "
                    f"phase={result_item.phase or 'unknown'})"
                ),
            )

        download_loc = result_item.download_location
        if not download_loc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Download location not found for result item",
            )

        download_loc = os.path.abspath(download_loc)
        md_path = os.path.join(download_loc, "summary.md")

        if not os.path.exists(md_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Base summary file not found at {md_path}",
            )

        fmt = requested_format.lower().strip(".")

        if fmt in ["docx", "doc"]:
            docx_path = os.path.join(download_loc, "summary.docx")
            if not os.path.exists(docx_path):
                generated = await self.directory_manager.create_docx_version(md_path)
                if not generated or not os.path.exists(generated):
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to generate DOCX file",
                    )
            return (
                docx_path,
                f"summary_{folder_entry_id}.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        elif fmt == "pdf":
            pdf_path = os.path.join(download_loc, "summary.pdf")
            if not os.path.exists(pdf_path):
                generated = await self.directory_manager.create_pdf_version(md_path)
                if not generated or not os.path.exists(generated):
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to generate PDF file",
                    )
            return (
                pdf_path,
                f"summary_{folder_entry_id}.pdf",
                "application/pdf",
            )

        elif fmt in ["md", "markdown"]:
            return (
                md_path,
                f"summary_{folder_entry_id}.md",
                "text/markdown",
            )

        elif fmt in ["txt", "text"]:
            txt_path = os.path.join(download_loc, "summary.txt")
            if not os.path.exists(txt_path):
                async with aiofiles.open(md_path, "r", encoding="utf-8") as f_in:
                    content = await f_in.read()
                async with aiofiles.open(txt_path, "w", encoding="utf-8") as f_out:
                    await f_out.write(content)
            return (
                txt_path,
                f"summary_{folder_entry_id}.txt",
                "text/plain",
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported download format: {requested_format}",
            )
