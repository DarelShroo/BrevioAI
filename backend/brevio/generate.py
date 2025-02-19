import asyncio
import uuid
import logging
from os import path
from typing import Union, overload
from bson import ObjectId
import torch
from os import environ
from backend.brevio.enums.content import ContentType
from backend.brevio.enums.language import LanguageType
from backend.brevio.models.summary_config_model import SummaryConfig
from backend.models.brevio.brevio_generate import BrevioGenerate, DurationEntry
from backend.models.user.data_result import DataResult
from backend.models.user.folder_entry import FolderEntry
from backend.models.user.user import User
from backend.models.user.user_folder import UserFolder
from .services.transcription_service import TranscriptionService
from .services.summary_service import SummaryService
from .services.yt_service import YTService as YTDownload
from .managers.directory_manager import DirectoryManager
from .models.response_model import SummaryResponse, TranscriptionResponse
from .constants.constants import Constants
from .constants.contents import Contents

logger = logging.getLogger(__name__)

environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

class Generate:
    def __init__(self):
        self._directory_manager = DirectoryManager()
        self._summary_service = SummaryService()
        self._transcription_service = TranscriptionService()
        self._yt_service = YTDownload()

    @overload
    async def organize_audio_files_into_folders(self) -> dict: ...

    @overload
    async def organize_audio_files_into_folders(
        self, data: list[dict]) -> dict: ...

    async def organize_audio_files_into_folders(self, data: Union[None, list[dict]] = None) -> dict:
        if data is None:
            return await self._process_local_audio_files()
        return await self._process_online_audio_data(data)

    async def _process_local_audio_files(self) -> dict:
        # Implementar procesamiento
        pass
    async def _process_online_audio_data(self, data: BrevioGenerate, _create_data_result, current_folder_entry: FolderEntry, _user_folder: UserFolder) -> dict:
        folder_id = _user_folder.id
        entry_id = current_folder_entry.id
        transcription_sem = asyncio.Semaphore(5)
        summary_sem = asyncio.Semaphore(5)
        
        async def process_video(index: int, video: DurationEntry):
            try:
                data_result = DataResult()
                destination_path = f"audios/{folder_id}/{entry_id}/{index}"
                audio_filename = f"{index}.mp3"
                audio_path = path.join(destination_path, audio_filename)
                transcription_path = path.join(
                    destination_path, Constants.TRANSCRIPTION_FILE)
                summary_path = path.join(
                    destination_path, Constants.SUMMARY_FILE)

                self._directory_manager.createFolder(destination_path)

                await self._yt_service.download(video.url, destination_path, str(index))


                if not await self._verify_file_exists(audio_path):
                    raise FileNotFoundError(
                        f"Error: No se encontró el archivo descargado {audio_path}")

                async with transcription_sem:
                    transcription_result = await asyncio.to_thread(
                        self._transcription_service.generate_transcription,
                        audio_path, destination_path, LanguageType[data.language]
                    )

                torch.cuda.empty_cache()

                async with summary_sem:
                    summary_config = SummaryConfig(
                    transcription_path, summary_path, ContentType[data.content], LanguageType[data.language], data.model)

                    summary_result = await asyncio.to_thread(
                        self._summary_service.generate_summary, summary_config)
                    
                torch.cuda.empty_cache()

                data_result.url = video.url
                data_result.download_location = destination_path
                data_result.index = index
                
                info = await self._yt_service.get_media_info(video.url)

                data_result.name = info["title"]
                data_result.duration = float(info["duration"]) if info["duration"] is not None else 0.0

                _create_data_result(folder_id, current_folder_entry, data_result)

                return {
                    "transcription": TranscriptionResponse(success=True).__str__(),
                    "summary": SummaryResponse(success=True).__str__()
                }
            
            except Exception as e:
                logger.error(f"Error procesando video {index}: {str(e)}")
                return {
                    "transcription": TranscriptionResponse(success=False, error_message=str(e)).__str__(),
                    "summary": SummaryResponse(success=False, error_message=str(e)).__str__()
                }

        tasks = [process_video(index, video)
                 for index, video in enumerate(data.data)]
        
        results = await asyncio.gather(*tasks)

        return {
            "folder_response": {"success": True, "message": "Directorios creados correctamente"},
            "download_response": {"success": True, "message": "Descargas completadas exitosamente"},
            "transcription_response": [r["transcription"] for r in results],
            "summary_response": [r["summary"] for r in results]
        }

    async def _verify_file_exists(self, file_path: str, max_attempts: int = 10) -> bool:
        for attempt in range(max_attempts):
            if path.exists(file_path):
                logger.debug(
                    f"Archivo encontrado: {file_path} en el intento {attempt+1}")
                return True
            await asyncio.sleep(0.5)
        logger.error(
            f"Archivo no encontrado después de {max_attempts} intentos: {file_path}")
        return False
