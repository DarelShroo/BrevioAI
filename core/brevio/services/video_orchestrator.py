import asyncio
import logging
import os
import shutil
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

class VideoOrchestrator:
    def __init__(
        self,
        directory_manager: DirectoryManager,
        summary_service: SummaryService,
        transcription_service: TranscriptionService,
        yt_service: YTService,
        audio_service: AudioService,
    ):
        self._directory_manager = directory_manager
        self._summary_service = summary_service
        self._transcription_service = transcription_service
        self._yt_service = yt_service
        self._audio_service = audio_service

    async def process_video(
        self,
        index: int,
        video: Any,
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

            # Create FileConfig for transcription
            file_config = FileConfig(
                transcription_path=transcription_path, summary_path=summary_path
            )
            
            # Generate summary
            summary_responses = await self._summary_service.generate_summary_documents(
                prompt_config=data.prompt_config,
                file_configs=[file_config]
            )
            
            if not summary_responses or not summary_responses[0].success:
                 error_msg = summary_responses[0].message if summary_responses else "Unknown error"
                 raise RuntimeError(f"Failed to generate summary: {error_msg}")

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
