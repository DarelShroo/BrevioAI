import asyncio
from concurrent.futures import ThreadPoolExecutor
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
from backend.brevio.services.audio_service import AudioService
from backend.models.brevio.brevio_generate import BrevioGenerate, MediaEntry
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
from os import listdir
logger = logging.getLogger(__name__)

environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"


class Generate:
    def __init__(self):
        self._directory_manager = DirectoryManager()
        self._summary_service = SummaryService()
        self._transcription_service = TranscriptionService()
        self._yt_service = YTDownload()
        self._audio_service = AudioService()
        self.semaphore = asyncio.Semaphore(5)
        self.executor = ThreadPoolExecutor(max_workers=10)

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

    async def _process_online_audio_data(self, data: BrevioGenerate, _create_data_result, current_folder_entry_id: str, _user_folder_id: str, _user_id: str) -> dict:
        transcription_sem = asyncio.Semaphore(5)
        summary_sem = asyncio.Semaphore(5)

        async def process_video(index: int, video: MediaEntry):
            try:
                data_result = DataResult()
                destination_path = f"audios/{_user_folder_id}/{current_folder_entry_id}/{index}"
                audio_filename = f"{index}.mp3" if video.url is not None else next(
                    file for file in listdir(destination_path) if file.endswith(".mp3"))

                audio_path = path.join(destination_path, audio_filename)
                transcription_path = path.join(
                    destination_path, Constants.TRANSCRIPTION_FILE)
                summary_path = path.join(
                    destination_path, Constants.SUMMARY_FILE)
                self._directory_manager.createFolder(destination_path)

                if video.url is not None:
                    await self._yt_service.download(video.url, destination_path, str(index))

                if not await self._verify_file_exists(audio_path):
                    raise FileNotFoundError(
                        f"Error: No se encontró el archivo descargado {audio_path}")

                async with transcription_sem:
                    transcription_result = await asyncio.to_thread(
                        self._transcription_service.generate_transcription,
                        audio_path, destination_path, data.language
                    )

                torch.cuda.empty_cache()

                async with summary_sem:
                    summary_config = SummaryConfig(
                        transcription_path=transcription_path,
                        summary_path=summary_path,
                        content=data.content,
                        language=data.language,
                        model=data.model
                    )

                    summary_result = await self._summary_service.generate_summary(summary_config)

                torch.cuda.empty_cache()

                data_result.url = video.url if video.url is not None else ""
                data_result.download_location = destination_path
                data_result.index = index

                info = None
                if video.url is not None:
                    info = await self._yt_service.get_media_info(video.url)
                else:
                    info = await self._audio_service.get_media_info(audio_path)

                data_result.name = info["title"]
                data_result.duration = float(
                    info["duration"]) if info["duration"] is not None else 0.0
                _create_data_result(
                    _user_id, current_folder_entry_id, data_result)

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

    async def _process_pdf(self, data: BrevioGenerate, _create_data_result, current_folder_entry_id: str, _user_folder_id: str, _user_id: str) -> dict:
        summary_sem = asyncio.Semaphore(5)

        async def process_pdf(index: int, pdf: MediaEntry):
            try:
                data_result = DataResult()
                destination_path = f"audios/{_user_folder_id}/{current_folder_entry_id}/{index}"
                summary_path = path.join(destination_path, Constants.SUMMARY_FILE)
                self._directory_manager.createFolder(destination_path)

                torch.cuda.empty_cache()
                async with summary_sem:
                    summary_config = SummaryConfig(
                        pdf_path=pdf.path,
                        summary_path=summary_path,
                        content=data.content,
                        language=data.language,
                        model=data.model
                    )

                    # Cambiar asyncio.to_thread por await directo
                    summary_result = await self._summary_service.generate_summary_pdf(summary_config)

                torch.cuda.empty_cache()

                data_result.download_location = destination_path
                data_result.index = index

                return {"summary": SummaryResponse(success=True).__str__()}
            except Exception as e:
                logger.error(f"Error procesando PDF {index}: {str(e)}")
                raise e

        tasks = [process_pdf(index, pdf) for index, pdf in enumerate(data.data)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error: {str(result)}")
                processed_results.append({
                    "summary": SummaryResponse(success=False, error_message=str(result)).__str__()
                })
            else:
                processed_results.append(result)

        return {
            "folder_response": {"success": True, "message": "Directorios creados correctamente"},
            "download_response": {"success": True, "message": "Descargas completadas exitosamente"},
            "summary_response": [r["summary"] for r in processed_results]
        }
    async def _process_docx(self, data: BrevioGenerate, _create_data_result, current_folder_entry_id: str, _user_folder_id: str, _user_id: str) -> dict:
        # Crear tareas para cada documento
        tasks = [
            self._process_single_docx(
                index, 
                docx, 
                data, 
                current_folder_entry_id, 
                _user_folder_id, 
                _user_id
            ) for index, docx in enumerate(data.data)
        ]
        
        # Ejecutar todas las tareas concurrentemente
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Procesar resultados
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error: {str(result)}")
                processed_results.append({
                    "summary": SummaryResponse(
                        success=False, 
                        error_message=str(result)
                    ).__str__()
                })
            else:
                processed_results.append(result)
        
        return {
            "folder_response": {"success": True, "message": "Directorios creados correctamente"},
            "download_response": {"success": True, "message": "Descargas completadas exitosamente"},
            "summary_response": [r["summary"] for r in processed_results]
        }

    async def _process_single_docx(self, index, docx, data, current_folder_entry_id, _user_folder_id, _user_id):
        try:
            data_result = DataResult()
            destination_path = f"audios/{_user_folder_id}/{current_folder_entry_id}/{index}"
            summary_path = path.join(destination_path, Constants.SUMMARY_FILE)
            self._directory_manager.createFolder(destination_path)
            
            # Crear configuración para el resumen
            summary_config = SummaryConfig(
                docx_path=docx.path,
                summary_path=summary_path,
                content=data.content,
                language=data.language,
                model=data.model
            )

            # Llamada asincrónica al servicio de resumen
            summary_result = await self._summary_service.generate_summary_docx(summary_config)
            
            data_result.download_location = destination_path
            data_result.index = index
            return {"summary": SummaryResponse(success=True).__str__()}
        except Exception as e:
            logger.error(f"Error procesando DOCX {index}: {str(e)}")
            return {"summary": SummaryResponse(success=False, error_message=str(e)).__str__()}
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