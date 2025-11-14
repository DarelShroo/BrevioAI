import asyncio
import logging
import os
import shutil
from os import environ, listdir, path
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import torch
from pydantic import HttpUrl

from core.brevio.constants.constants import Constants
from core.brevio.managers.directory_manager import DirectoryManager
from core.brevio.models.file_config_model import FileConfig
from core.brevio.models.response_model import SummaryResponse, TranscriptionResponse
from core.brevio.services.audio_service import AudioService
from core.brevio.services.summary_service import SummaryService
from core.brevio.services.transcription_service import TranscriptionService
from core.brevio.services.yt_service import YTService
from core.shared.models.brevio.brevio_generate import BrevioGenerate
from core.shared.models.user.data_result import DataResult

logger = logging.getLogger(__name__)

environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"


class UsageCostTracker:
    """Placeholder for usage cost tracker with cost breakdown methods."""

    def get_cost_breakdown(self) -> Dict[str, Any]:
        return {}

    def get_total_cost(self) -> float:
        return 0.0


class Generate:
    def __init__(self) -> None:
        try:
            self._directory_manager = DirectoryManager()
            self._summary_service = SummaryService()
            self._transcription_service = TranscriptionService()
            self._yt_service = YTService()
            self._audio_service = AudioService()
            logger.info("Generate class initialized successfully")
        except Exception as e:
            logger.error(
                f"Failed to initialize Generate class: {str(e)}", exc_info=True
            )
            raise RuntimeError(f"Initialization failed: {str(e)}")

    async def _process_local_audio_files(self) -> Dict[str, Any]:
        """Process local audio files (not implemented)."""
        logger.warning("_process_local_audio_files not implemented")
        raise NotImplementedError("Local audio file processing not implemented")

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
        try:
            data_result = DataResult(name=f"Video {index}")
            destination_path = f"{Constants.DESTINATION_FOLDER}/{_user_folder_id}/{current_folder_entry_id}/{index}"
            await asyncio.to_thread(os.makedirs, destination_path, exist_ok=True)

            audio_filename = (
                os.path.basename(video.path)
                if getattr(video, "path", None)
                else f"{index}.mp3"
            )
            audio_path = os.path.join(destination_path, audio_filename)
            transcription_path = os.path.join(
                destination_path, Constants.TRANSCRIPTION_FILE
            )
            summary_path = os.path.join(destination_path, Constants.SUMMARY_FILE)

            if getattr(video, "url", None):
                await self._yt_service.download(
                    HttpUrl(video.url), destination_path, str(index)
                )
            elif getattr(video, "path", None):
                src_path = Path(video.path)
                dest_path = Path(audio_path)
                if not await asyncio.to_thread(src_path.exists):
                    raise FileNotFoundError(f"Fichero no encontrado: {video.path}")
                if src_path.resolve() != dest_path.resolve():
                    await asyncio.to_thread(shutil.copy, src_path, dest_path)
                else:
                    logger.info(
                        f"El archivo ya está en la ubicación de destino: {dest_path}"
                    )
            else:
                raise ValueError(f"No URL ni path proporcionado para video {index}")

            if not await self._verify_file_exists(Path(audio_path)):
                raise FileNotFoundError(f"Archivo de audio no encontrado: {audio_path}")

            await self._transcription_service.generate_transcription(
                audio_path, destination_path, data.prompt_config.language
            )
            if not await self._verify_file_exists(Path(transcription_path)):
                raise FileNotFoundError(
                    f"Archivo de transcripción no creado: {transcription_path}"
                )

            await self._summary_service._process_single_transcription(
                prompt_config=data.prompt_config,
                file_config=FileConfig(
                    transcription_path=transcription_path, summary_path=summary_path
                ),
                data_result=data_result,
            )
            if not await self._verify_file_exists(Path(summary_path)):
                raise FileNotFoundError(f"Archivo de resumen no creado: {summary_path}")

            await asyncio.to_thread(torch.cuda.empty_cache)

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
                data_result.duration = 0.0

            await _create_data_result(_user_id, current_folder_entry_id, data_result)

            return {
                "transcription": TranscriptionResponse(success=True).__str__(),
                "summary": SummaryResponse(success=True).__str__(),
            }

        except Exception as e:
            logger.error(f"Error processing video {index}: {str(e)}", exc_info=True)
            raise

    async def _process_online_audio_data(
        self,
        data: BrevioGenerate,
        _create_data_result: Callable[[str, str, DataResult], Any],
        current_folder_entry_id: str,
        _user_folder_id: str,
        _user_id: str,
        _usage_cost_tracker: Optional[UsageCostTracker] = None,
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
        _usage_cost_tracker: Optional[UsageCostTracker] = None,
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
                    _usage_cost_tracker,
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
        _usage_cost_tracker: Optional[UsageCostTracker] = None,
    ) -> Dict[str, str]:
        try:
            data_result = DataResult(name=f"Document {index}")
            destination_path = f"{Constants.DESTINATION_FOLDER}/{_user_folder_id}/{current_folder_entry_id}/{index}"
            summary_path = path.join(destination_path, Constants.SUMMARY_FILE)

            logger.info(f"Processing document {index} at {destination_path}")

            await self._directory_manager.createFolder(destination_path)

            _file_config = FileConfig(
                summary_path=summary_path, document_path=document_path
            )

            summary_result = await self._summary_service.generate_summary_document(
                _data.prompt_config, _file_config
            )

            data_result.download_location = destination_path
            data_result.index = index

            if _create_data_result is not None and _user_id and current_folder_entry_id:
                await _create_data_result(
                    _user_id, current_folder_entry_id, data_result
                )
            else:
                logger.warning(
                    "create_data_result or user_id or current_folder_entry_id is None"
                )
            if _usage_cost_tracker:
                logger.info(
                    f"costo_total_detallado: {_usage_cost_tracker.get_cost_breakdown()}"
                )
                logger.info(f"costo_total: {_usage_cost_tracker.get_total_cost()}")

            return {"summary": SummaryResponse(success=True).__str__()}
        except FileNotFoundError as e:
            logger.error(f"File not found for document {index}: {str(e)}")
            raise
        except ValueError as e:
            logger.error(f"Invalid data for document {index}: {str(e)}")
            raise ValueError(f"Invalid document data: {str(e)}")
        except Exception as e:
            logger.error(
                f"Unexpected error processing document {index}: {str(e)}", exc_info=True
            )
            raise RuntimeError(f"Failed to process document {index}: {str(e)}")

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
