import asyncio
import datetime
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from os import environ, listdir, path
from typing import Any, Callable, Dict, Optional, TypedDict

import torch
from bson import ObjectId

from core.brevio.constants.constants import Constants
from core.brevio.managers.directory_manager import DirectoryManager
from core.brevio.models.file_config_model import FileConfig
from core.brevio.models.response_model import (
    FolderResponse,
    SummaryResponse,
    TranscriptionResponse,
)
from core.brevio.services.audio_service import AudioService
from core.brevio.services.summary_service import SummaryService
from core.brevio.services.transcription_service import TranscriptionService
from core.brevio.services.yt_service import YTService
from core.shared.models.brevio.brevio_generate import BrevioGenerate
from core.shared.models.user.data_result import DataResult

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"


class UsageCostTracker:
    """Placeholder for usage cost tracker with cost breakdown methods."""

    def get_cost_breakdown(self) -> Dict[str, Any]:
        return {}

    def get_total_cost(self) -> float:
        return 0.0


class Generate:
    """Class to handle generation of transcriptions and summaries for audio and documents."""

    def __init__(self) -> None:
        """Initialize Generate class with necessary services."""
        try:
            self._directory_manager = DirectoryManager()
            self._summary_service = SummaryService()
            self._transcription_service = TranscriptionService()
            self._yt_service = YTService()
            self._audio_service = AudioService()
            self.semaphore = asyncio.Semaphore(5)
            self.executor = ThreadPoolExecutor(max_workers=10)
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

    async def _process_online_audio_data(
        self,
        data: BrevioGenerate,
        _create_data_result: Optional[Callable[[ObjectId, ObjectId, DataResult], Any]],
        current_folder_entry_id: ObjectId,
        _user_folder_id: ObjectId,
        _user_id: Optional[ObjectId] = None,
        _usage_cost_tracker: Optional[UsageCostTracker] = None,
    ) -> Dict[str, Any]:
        """Process online audio data, generating transcriptions and summaries."""
        from core.brevio_api.services.billing.billing_estimator_service import (
            BillingEstimatorService,
        )

        _billing_estimator_service = BillingEstimatorService()

        transcription_sem = asyncio.Semaphore(5)
        summary_sem = asyncio.Semaphore(5)

        async def process_video(index: int, video: Any) -> Dict[str, str]:
            try:
                data_result = DataResult(name=f"Video {index}")
                destination_path = f"{Constants.DESTINATION_FOLDER}/{_user_folder_id}/{current_folder_entry_id}/{index}"
                os.makedirs(destination_path, exist_ok=True)
                audio_filename = (
                    f"{index}.mp3"
                    if video.url
                    else next(
                        (
                            file
                            for file in listdir(destination_path)
                            if file.endswith(".mp3")
                        ),
                        "default.mp3",
                    )
                )
                transcription_path = os.path.join(
                    destination_path, Constants.TRANSCRIPTION_FILE
                )
                summary_path = os.path.join(destination_path, Constants.SUMMARY_FILE)
                audio_path = os.path.join(destination_path, audio_filename)

                logger.info(f"Processing video {index} at {destination_path}")
                await asyncio.to_thread(
                    self._directory_manager.createFolder, destination_path
                )

                _file_config = FileConfig(
                    transcription_path=transcription_path, summary_path=summary_path
                )

                if video.url:
                    await self._yt_service.download(
                        video.url, destination_path, str(index)
                    )

                if not await self._verify_file_exists(audio_path):
                    raise FileNotFoundError(f"Downloaded file not found: {audio_path}")
                async with transcription_sem:
                    start_time = datetime.datetime.now()

                    await self._transcription_service.generate_transcription(
                        audio_path, destination_path, data.prompt_config.language
                    )

                    if not await self._verify_file_exists(transcription_path):
                        raise FileNotFoundError(
                            f"Transcription file not created: {transcription_path}"
                        )
                    logger.debug(f"Transcription completed for video {index}")
                    end_time = datetime.datetime.now()

                async with summary_sem:
                    await self._summary_service.generate_summary_document(
                        prompt_config=data.prompt_config,
                        file_config=_file_config,
                    )
                    if not await self._verify_file_exists(summary_path):
                        raise FileNotFoundError(
                            f"Summary file not created: {summary_path}"
                        )
                    logger.debug(f"Summary completed for video {index}")

                await asyncio.get_event_loop().run_in_executor(
                    self.executor, torch.cuda.empty_cache
                )

                data_result.url = str(video.url) if video.url else ""
                data_result.download_location = destination_path
                data_result.index = index

                info = (
                    await (
                        self._audio_service.get_media_info_yt(video.url)
                        if video.url
                        else self._audio_service.get_media_info(audio_path)
                    )
                    or {}
                )

                data_result.name = info.get("title", f"Video {index}")
                data_result.duration = (
                    float(info["duration"]) if info.get("duration") else 0.0
                )

                if (
                    _create_data_result is not None
                    and _user_id
                    and current_folder_entry_id
                ):
                    await _create_data_result(
                        _user_id, current_folder_entry_id, data_result
                    )
                else:
                    logger.warning(
                        "create_data_result or user_id or current_folder_entry_id is None"
                    )

                return {
                    "transcription": TranscriptionResponse(success=True).__str__(),
                    "summary": SummaryResponse(success=True).__str__(),
                }

            except Exception as e:
                logger.error(f"Error processing video {index}: {str(e)}", exc_info=True)
                raise

        try:
            tasks = []
            for index, video in enumerate(data.data):
                task = process_video(index, video)
                tasks.append(task)

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
                    "message": "Descargas completadas exitosamente",
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
        current_folder_entry_id: Optional[ObjectId] = None,
        _user_folder_id: Optional[ObjectId] = None,
        _user_id: Optional[ObjectId] = None,
        _create_data_result: Optional[
            Callable[[ObjectId, ObjectId, DataResult], Any]
        ] = None,
        _usage_cost_tracker: Optional[UsageCostTracker] = None,
    ) -> Dict[str, Any]:
        """Process documents to generate summaries."""
        try:
            tasks = [
                self._process_single_document(
                    index,
                    str(document.path),
                    _data,
                    str(current_folder_entry_id) if current_folder_entry_id else None,
                    str(_user_folder_id) if _user_folder_id else None,
                    str(_user_id) if _user_id else None,
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
        current_folder_entry_id: Optional[str] = None,
        _user_folder_id: Optional[str] = None,
        _user_id: Optional[str] = None,
        _create_data_result: Optional[
            Callable[[ObjectId, ObjectId, DataResult], Any]
        ] = None,
        _usage_cost_tracker: Optional[UsageCostTracker] = None,
    ) -> Dict[str, str]:
        """Process a single document to generate a summary."""
        try:
            data_result = DataResult(name=f"Document {index}")
            destination_path = f"{Constants.DESTINATION_FOLDER}/{_user_folder_id}/{current_folder_entry_id}/{index}"
            summary_path = path.join(destination_path, Constants.SUMMARY_FILE)

            logger.info(f"Processing document {index} at {destination_path}")

            self._directory_manager.createFolder(destination_path)

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
                    ObjectId(_user_id), ObjectId(current_folder_entry_id), data_result
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

    async def _verify_file_exists(self, file_path: str, max_attempts: int = 10) -> bool:
        """Verify if a file exists, retrying up to max_attempts times."""
        try:
            for attempt in range(max_attempts):
                if path.exists(file_path):
                    logger.debug(f"File found: {file_path} on attempt {attempt + 1}")
                    return True
                await asyncio.sleep(0.5)
            logger.error(f"File not found after {max_attempts} attempts: {file_path}")
            raise FileNotFoundError(
                f"File not found after {max_attempts} attempts: {file_path}"
            )
        except Exception as e:
            logger.error(
                f"Error verifying file existence {file_path}: {str(e)}", exc_info=True
            )
            raise Exception(f"Error verifying file existence {file_path}")
