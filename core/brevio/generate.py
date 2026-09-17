import asyncio
import logging
import os
from os import environ, path
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from pydantic import HttpUrl

from core.brevio.constants.constants import Constants
from core.brevio.managers.directory_manager import DirectoryManager
from core.brevio.models.file_config_model import FileConfig
from core.brevio.models.response_model import SummaryResponse, TranscriptionResponse
from core.brevio.services.audio_service import AudioService
from core.brevio.services.input import media_input_provider_for
from core.brevio.services.summary_pipeline import (
    PipelineDocumentError,
    job_phase_for,
    job_status_for,
)
from core.brevio.services.summary_service import SummaryService
from core.brevio.services.transcription.catalog import resolve_media_provider
from core.brevio.services.transcription.errors import TranscriptionError
from core.brevio.services.transcription.redact import redact_secrets
from core.brevio.services.transcription_service import TranscriptionService
from core.brevio.services.yt_service import YTService
from core.brevio_api.models.errors.api_codes import ApiErrorCode
from core.shared.enums.job_status import JobPhase, JobStatus
from core.shared.models.brevio.brevio_generate import BrevioGenerate
from core.shared.models.user.data_result import DataResult
from core.shared.utils.source_names import names_for_source

logger = logging.getLogger(__name__)

# Only relevant when local Whisper / PyTorch are installed (requirements.dev.txt).
environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")


def _empty_cuda_cache() -> None:
    """Release CUDA memory when torch is available; no-op in production images."""
    try:
        import torch
    except ImportError:
        return
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


class _ResultWriter:
    """Adapts UserService (or a test mock) for PROGRESS and terminal writes."""

    def __init__(self, create_fn: Optional[Callable]) -> None:
        self._create = create_fn
        self._svc = (
            getattr(create_fn, "__self__", None) if create_fn is not None else None
        )
        self._reporter = None

    def _can_update(self) -> bool:
        return self._svc is not None and hasattr(self._svc, "update_data_result_status")

    def _get_reporter(self, user_id: str, folder_id: str) -> Optional[Any]:
        if self._reporter:
            return self._reporter
        if not self._can_update():
            return None
        repo = getattr(self._svc, "_folder_entry_repo", None)
        if not repo:
            return None
        try:
            from core.brevio_api.services.progress.reporter import ProgressReporter
            self._reporter = ProgressReporter(repo, user_id, folder_id)
            return self._reporter
        except ImportError:
            return None

    async def start(self, user_id: str, folder_id: str, result: DataResult) -> None:
        if self._create is None or not user_id or not folder_id:
            return
        if not self._can_update():
            return
        await self._create(user_id, folder_id, result)
        reporter = self._get_reporter(user_id, folder_id)
        if reporter:
            await reporter.update_item_progress(
                document_id=str(result.id),
                result=result,
                progress=0,
                stage=result.phase or "QUEUED",
                force_persist=True
            )

    async def finish(
        self,
        user_id: str,
        folder_id: str,
        result: DataResult,
        *,
        success: bool,
        phase: str,
        error_type: str = "",
        error_code: str = "",
        error_message: str = "",
        download_location: Optional[str] = None,
        name: Optional[str] = None,
        index: Optional[int] = None,
    ) -> None:
        if self._create is None or not user_id or not folder_id:
            return
        status = job_status_for(success=success).value
        
        reporter = self._get_reporter(user_id, folder_id)
        if reporter and result.id:
            if download_location:
                result.download_location = download_location
            if name:
                result.name = name
            if index is not None:
                result.index = index
            if error_type:
                result.error_type = error_type
            if error_code:
                result.error_code = error_code
            if error_message:
                result.error_message = error_message

            if success:
                await reporter.complete_item(str(result.id), result)
            else:
                await reporter.fail_item(str(result.id), result, error_message or "FAILED")
            return

        if self._can_update():
            await self._svc.update_data_result_status(
                user_id,
                folder_id,
                result,
                status=status,
                phase=phase,
                success=success,
                error_type=error_type or None,
                error_code=error_code or None,
                error_message=error_message or None,
                download_location=download_location,
                name=name,
                index=index,
            )
            return
        result.status = status
        result.phase = phase
        result.success = success
        if error_type:
            result.error_type = error_type
        if error_code:
            result.error_code = error_code
        if error_message:
            result.error_message = error_message
        if download_location:
            result.download_location = download_location
        if name:
            result.name = name
        if index is not None:
            result.index = index
        await self._create(user_id, folder_id, result)

    async def progress(
        self,
        user_id: str,
        folder_id: str,
        result: DataResult,
        *,
        phase: str,
        progress: int = 50,
    ) -> None:
        if self._create is None or not user_id or not folder_id:
            return
        
        reporter = self._get_reporter(user_id, folder_id)
        if reporter and result.id:
            await reporter.update_item_progress(
                document_id=str(result.id),
                result=result,
                progress=progress,
                stage=phase
            )
            return

        if not self._can_update():
            result.phase = phase
            result.status = JobStatus.PROCESSING.value
            return
        await self._svc.update_data_result_status(
            user_id,
            folder_id,
            result,
            status=JobStatus.PROCESSING.value,
            phase=phase,
            success=False,
        )


class Generate:
    def __init__(self) -> None:
        try:
            self._directory_manager = DirectoryManager()
            self._summary_service = SummaryService()
            self._transcription_service = TranscriptionService()
            self._transcription_service.set_credential_resolver(
                getattr(self._summary_service, "credential_resolver", None)
            )
            self._yt_service = YTService()
            self._audio_service = AudioService()
            logger.info("Generate class initialized successfully")
        except Exception as e:
            logger.error(
                f"Failed to initialize Generate class: {str(e)}", exc_info=True
            )
            raise RuntimeError(f"Initialization failed: {str(e)}")

    async def _process_local_audio_files(
        self,
        data: BrevioGenerate,
        _create_data_result: Callable[[str, str, DataResult], Any],
        current_folder_entry_id: str,
        _user_folder_id: str,
        _user_id: str,
    ) -> Dict[str, Any]:
        """Local uploads use the same media path as online/YouTube items."""
        return await self._process_online_audio_data(
            data,
            _create_data_result,
            current_folder_entry_id,
            _user_folder_id,
            _user_id,
        )

    async def process_video(
        self,
        index: int,
        video: Any,  # Objeto con `url` o `path`
        data: BrevioGenerate,
        _create_data_result: Callable[[str, str, DataResult], Any],
        current_folder_entry_id: str,
        _user_folder_id: str,
        _user_id: str,
    ) -> Dict[str, str]:
        writer: Optional[_ResultWriter] = None
        data_result: Optional[DataResult] = None
        terminal_written = False
        destination_path = f"{Constants.DESTINATION_FOLDER}/{_user_folder_id}/{current_folder_entry_id}/{index}"
        try:
            source = getattr(video, "path", None) or getattr(video, "url", None)
            display_name, original_name = names_for_source(
                str(source or ""), index, kind="video"
            )
            data_result = DataResult(
                name=display_name,
                original_name=original_name,
                index=index,
                download_location=destination_path,
                status=JobStatus.PROCESSING.value,
                phase=JobPhase.TRANSCRIBING.value,
                success=False,
            )
            writer = _ResultWriter(_create_data_result)
            await asyncio.to_thread(os.makedirs, destination_path, exist_ok=True)
            await writer.start(_user_id, current_folder_entry_id, data_result)

            input_provider = media_input_provider_for(
                video, yt_service=self._yt_service
            )
            acquired = await input_provider.acquire(Path(destination_path), index)
            audio_path = acquired.audio_path
            transcription_path = os.path.join(
                destination_path, Constants.TRANSCRIPTION_FILE
            )
            summary_path = os.path.join(destination_path, Constants.SUMMARY_FILE)

            if not await self._verify_file_exists(Path(audio_path)):
                raise FileNotFoundError(f"Archivo de audio no encontrado: {audio_path}")

            provider = resolve_media_provider(
                getattr(data, "transcription_provider", None)
            ).value
            transcription_model = getattr(data, "transcription_model", None)

            summary_exists = await asyncio.to_thread(
                lambda: os.path.exists(summary_path)
                and os.path.getsize(summary_path) > 0
            )
            if not summary_exists:
                await writer.progress(
                    _user_id,
                    current_folder_entry_id,
                    data_result,
                    phase=JobPhase.TRANSCRIBING.value,
                    progress=20,
                )
                await self._transcription_service.generate_transcription(
                    audio_path,
                    destination_path,
                    data.prompt_config.language,
                    provider=provider,
                    user_id=_user_id,
                    enforce_user_access=True,
                    skip_if_exists=True,
                    model=transcription_model,
                )
                if not await self._verify_file_exists(Path(transcription_path)):
                    raise FileNotFoundError(
                        f"Archivo de transcripción no creado: {transcription_path}"
                    )
                await writer.progress(
                    _user_id,
                    current_folder_entry_id,
                    data_result,
                    phase=JobPhase.TRANSCRIBED.value,
                    progress=50,
                )

                summary_result = (
                    await self._summary_service._process_single_transcription(
                        prompt_config=data.prompt_config,
                        file_config=FileConfig(
                            transcription_path=transcription_path,
                            document_path=transcription_path,
                            summary_path=summary_path,
                        ),
                        data_result=data_result,
                        folder_id=current_folder_entry_id,
                        user_id=_user_id,
                    )
                )
                if not summary_result.success:
                    raise PipelineDocumentError(summary_result)
                if not await self._verify_file_exists(Path(summary_path)):
                    raise FileNotFoundError(
                        f"Archivo de resumen no creado: {summary_path}"
                    )
                job_phase = (
                    getattr(summary_result, "job_phase", "")
                    or job_phase_for(
                        getattr(summary_result, "phase", "") or JobPhase.FAILED.value,
                        success=True,
                    ).value
                )
            else:
                job_phase = JobPhase.COMPLETED.value
                summary_result = SummaryResponse(success=True, summary="")

            await asyncio.to_thread(_empty_cuda_cache)

            data_result.download_location = destination_path
            data_result.index = index

            if getattr(video, "url", None):
                data_result.url = video.url
                info = (
                    await self._audio_service.get_media_info_yt(HttpUrl(video.url))
                    or {}
                )
                data_result.name = info.get("title", f"Video {index}")
                data_result.duration = float(info.get("duration", 0.0))
            else:
                data_result.url = None
                data_result.name = os.path.basename(video.path)
                duration = getattr(video, "duration", None)
                data_result.duration = float(duration or 0.0)

            await writer.finish(
                _user_id,
                current_folder_entry_id,
                data_result,
                success=True,
                phase=job_phase if summary_exists else JobPhase.COMPLETED.value,
                download_location=destination_path,
                name=data_result.name,
                index=index,
            )
            terminal_written = True

            return {
                "transcription": TranscriptionResponse(success=True).__str__(),
                "summary": summary_result.to_dict()
                if hasattr(summary_result, "to_dict")
                else SummaryResponse(success=True).__str__(),
            }

        except Exception as e:
            logger.error(
                "Error processing video %s: %s",
                index,
                redact_secrets(str(e)),
                exc_info=True,
            )
            if writer and data_result and not terminal_written:
                await self._persist_failure_quietly(
                    writer,
                    _user_id,
                    current_folder_entry_id,
                    data_result,
                    e,
                    destination_path,
                    index,
                )
            raise

    async def _process_online_audio_data(
        self,
        data: BrevioGenerate,
        _create_data_result: Callable[[str, str, DataResult], Any],
        current_folder_entry_id: str,
        _user_folder_id: str,
        _user_id: str,
    ) -> Dict[str, Any]:
        try:
            tasks = []
            task_index = 0

            for video in data.data:
                url = getattr(video, "url", None)

                if url is not None and await self._yt_service.is_youtube_playlist(url):
                    video_urls = await self._yt_service.get_video_urls_from_playlist(
                        HttpUrl(url)
                    )
                    for video_url in video_urls:
                        video_obj = type("VideoObj", (object,), {"url": video_url})()
                        tasks.append(
                            self.process_video(
                                index=task_index,
                                video=video_obj,
                                data=data,
                                _create_data_result=_create_data_result,
                                current_folder_entry_id=current_folder_entry_id,
                                _user_folder_id=_user_folder_id,
                                _user_id=_user_id,
                            )
                        )
                        task_index += 1

                else:
                    tasks.append(
                        self.process_video(
                            index=task_index,
                            video=video,
                            data=data,
                            _create_data_result=_create_data_result,
                            current_folder_entry_id=current_folder_entry_id,
                            _user_folder_id=_user_folder_id,
                            _user_id=_user_id,
                        )
                    )
                    task_index += 1

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Task failed with exception: {str(result)}")
                    raise result

            return {
                "folder_response": {
                    "success": True,
                    "message": "Directorios creados correctamente",
                },
                "download_response": {
                    "success": True,
                    "message": "Procesamiento completado",
                },
                "transcription_response": [
                    r["transcription"]
                    for r in results
                    if isinstance(r, dict) and "transcription" in r
                ],
                "summary_response": [
                    r["summary"]
                    for r in results
                    if isinstance(r, dict) and "summary" in r
                ],
            }

        except Exception as e:
            logger.error(f"Error in online audio processing: {str(e)}", exc_info=True)
            raise

    async def _process_documents(
        self,
        _data: BrevioGenerate,
        current_folder_entry_id: str,
        _user_folder_id: str,
        _user_id: str,
        _create_data_result: Optional[Callable[[str, str, DataResult], Any]] = None,
    ) -> Dict[str, Any]:
        try:
            tasks = [
                self._process_single_document(
                    index,
                    str(document.path),
                    _data,
                    str(current_folder_entry_id),
                    str(_user_folder_id),
                    str(_user_id),
                    _create_data_result,
                )
                for index, document in enumerate(_data.data)
            ]
            results = await asyncio.gather(*tasks)

            return {
                "folder_response": {
                    "success": True,
                    "message": "Directorios creados correctamente",
                },
                "download_response": {
                    "success": True,
                    "message": "Descargas completadas exitosamente",
                },
                "summary_response": [r["summary"] for r in results],
            }
        except Exception as e:
            logger.error(f"Error processing documents: {str(e)}", exc_info=True)
            raise

    async def _process_single_document(
        self,
        index: int,
        document_path: str,
        _data: BrevioGenerate,
        current_folder_entry_id: str,
        _user_folder_id: str,
        _user_id: str,
        _create_data_result: Optional[Callable[[str, str, DataResult], Any]] = None,
    ) -> Dict[str, str]:
        writer: Optional[_ResultWriter] = None
        data_result: Optional[DataResult] = None
        destination_path = f"{Constants.DESTINATION_FOLDER}/{_user_folder_id}/{current_folder_entry_id}/{index}"
        terminal_written = False
        try:
            summary_path = path.join(destination_path, Constants.SUMMARY_FILE)
            display_name, original_name = names_for_source(
                document_path, index, kind="document"
            )
            data_result = DataResult(
                name=display_name,
                original_name=original_name,
                index=index,
                download_location=destination_path,
                status=JobStatus.PROCESSING.value,
                phase=JobPhase.QUEUED.value,
                success=False,
            )
            writer = _ResultWriter(_create_data_result)
            logger.info(f"Processing document {index} at {destination_path}")
            await writer.start(_user_id, current_folder_entry_id, data_result)
            await self._directory_manager.createFolder(destination_path)

            _file_config = FileConfig(
                summary_path=summary_path, document_path=document_path
            )

            async def _on_progress(progress: int, stage: str) -> None:
                if writer and data_result:
                    await writer.progress(
                        _user_id,
                        current_folder_entry_id,
                        data_result,
                        phase=stage,
                        progress=progress,
                    )

            try:
                summary_result = await self._summary_service.generate_summary_document(
                    _data.prompt_config,
                    _file_config,
                    folder_id=current_folder_entry_id,
                    user_id=_user_id,
                    progress_callback=_on_progress,
                )
            except Exception as pipeline_error:
                await self._persist_failure_quietly(
                    writer,
                    _user_id,
                    current_folder_entry_id,
                    data_result,
                    pipeline_error,
                    destination_path,
                    index,
                )
                terminal_written = True
                raise

            job_phase = (
                getattr(summary_result, "job_phase", "")
                or job_phase_for(
                    getattr(summary_result, "phase", "") or JobPhase.FAILED.value,
                    success=bool(summary_result.success),
                ).value
            )
            try:
                await writer.finish(
                    _user_id,
                    current_folder_entry_id,
                    data_result,
                    success=bool(summary_result.success),
                    phase=job_phase,
                    error_type=getattr(summary_result, "error_type", "") or "",
                    error_code=getattr(summary_result, "phase", "") or "",
                    error_message=(
                        getattr(summary_result, "error_message", "")
                        or getattr(summary_result, "message", "")
                    ),
                    download_location=destination_path,
                    name=data_result.name,
                    index=index,
                )
                terminal_written = True
            except Exception as persist_error:
                logger.error(
                    "Failed to persist terminal DataResult status for document %s: %s",
                    index,
                    persist_error,
                    exc_info=True,
                )
                if summary_result.success:
                    raise

            if not summary_result.success:
                raise PipelineDocumentError(summary_result)

            return {"summary": summary_result.to_dict()}
        except PipelineDocumentError as pipeline_done:
            if writer and data_result and not terminal_written:
                await self._persist_failure_quietly(
                    writer,
                    _user_id,
                    current_folder_entry_id,
                    data_result,
                    pipeline_done,
                    destination_path,
                    index,
                )
            raise
        except FileNotFoundError as e:
            logger.error(f"File not found for document {index}: {str(e)}")
            if writer and data_result and not terminal_written:
                await self._persist_failure_quietly(
                    writer,
                    _user_id,
                    current_folder_entry_id,
                    data_result,
                    e,
                    destination_path,
                    index,
                )
            raise
        except ValueError as e:
            logger.error(f"Invalid data for document {index}: {str(e)}")
            if writer and data_result and not terminal_written:
                await self._persist_failure_quietly(
                    writer,
                    _user_id,
                    current_folder_entry_id,
                    data_result,
                    e,
                    destination_path,
                    index,
                )
            raise ValueError(f"Invalid document data: {str(e)}") from e
        except Exception as e:
            logger.error(
                f"Unexpected error processing document {index}: {str(e)}", exc_info=True
            )
            if writer and data_result and not terminal_written:
                await self._persist_failure_quietly(
                    writer,
                    _user_id,
                    current_folder_entry_id,
                    data_result,
                    e,
                    destination_path,
                    index,
                )
            raise RuntimeError(f"Failed to process document {index}: {str(e)}") from e

    async def _persist_failure_quietly(
        self,
        writer: _ResultWriter,
        user_id: str,
        folder_id: str,
        result: DataResult,
        error: BaseException,
        destination_path: str,
        index: int,
    ) -> None:
        try:
            if isinstance(error, TranscriptionError):
                phase = error.phase or JobPhase.TRANSCRIBING.value
                error_code = error.code
                error_type = "TranscriptionError"
                error_message = error.code
            elif isinstance(error, PipelineDocumentError):
                summary = getattr(error, "result", None) or getattr(
                    error, "summary", None
                )
                phase = (
                    getattr(summary, "job_phase", "")
                    or getattr(summary, "phase", "")
                    or JobPhase.FAILED.value
                )
                error_code = ApiErrorCode.SUMMARY_AFTER_TRANSCRIPTION_FAILED.value
                error_type = getattr(summary, "error_type", "") or type(error).__name__
                error_message = (
                    getattr(summary, "error_message", "")
                    or getattr(summary, "message", "")
                    or ApiErrorCode.SUMMARY_AFTER_TRANSCRIPTION_FAILED.value
                )
                try:
                    phase = job_phase_for(phase, success=False).value
                except Exception:
                    phase = JobPhase.FAILED.value
            else:
                phase = getattr(error, "phase", "") or JobPhase.FAILED.value
                try:
                    phase = job_phase_for(phase, success=False).value
                except Exception:
                    phase = JobPhase.FAILED.value
                error_type = type(error).__name__
                error_code = (
                    getattr(error, "code", "")
                    or getattr(error, "phase", "")
                    or type(error).__name__
                )
                error_message = redact_secrets(str(error))
            await writer.finish(
                user_id,
                folder_id,
                result,
                success=False,
                phase=phase,
                error_type=error_type,
                error_code=error_code,
                error_message=error_message,
                download_location=destination_path,
                name=result.name,
                index=index,
            )
        except Exception as persist_error:
            logger.error(
                "Failed to persist FAILED DataResult for document %s: %s",
                index,
                persist_error,
                exc_info=True,
            )

    async def _verify_file_exists(
        self, file_path: Path, max_attempts: int = 10
    ) -> bool:
        for attempt in range(max_attempts):
            exists = await asyncio.to_thread(file_path.exists)
            if exists:
                return True
            await asyncio.sleep(0.5)
        raise FileNotFoundError(
            f"File not found after {max_attempts} attempts: {file_path}"
        )
