import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
from os import path
from typing import Union, overload
import torch
from os import environ
from ..brevio.models.file_config_model import FileConfig
from ..brevio.services.audio_service import AudioService
from ..models.brevio.brevio_generate import BrevioGenerate, MediaEntry
from ..models.user.data_result import DataResult
from .services import TranscriptionService, SummaryService, YTService as YTDownload
from .managers.directory_manager import DirectoryManager
from .models.response_model import SummaryResponse, TranscriptionResponse
from .constants.constants import Constants
from os import listdir, path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

class Generate:
    def __init__(self):
        try:
            self._directory_manager = DirectoryManager()
            self._summary_service = SummaryService()
            self._transcription_service = TranscriptionService()
            self._yt_service = YTDownload()
            self._audio_service = AudioService()
            self.semaphore = asyncio.Semaphore(5)
            self.executor = ThreadPoolExecutor(max_workers=10)
            logger.info("Generate class initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Generate class: {str(e)}", exc_info=True)
            raise RuntimeError(f"Initialization failed: {str(e)}")

    @overload
    async def organize_audio_files_into_folders(self) -> dict: ...

    @overload
    async def organize_audio_files_into_folders(self, data: list[dict]) -> dict: ...

    async def organize_audio_files_into_folders(self, data: Union[None, list[dict]] = None) -> dict:
        try:
            if data is None:
                logger.info("Processing local audio files")
                return await self._process_local_audio_files()
            logger.info("Processing online audio data")
            return await self._process_online_audio_data(data)
        except ValueError as e:
            logger.error(f"Invalid input data: {str(e)}", exc_info=True)
            raise ValueError(f"Invalid input data: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in organize_audio_files_into_folders: {str(e)}", exc_info=True)
            raise RuntimeError(f"Processing failed: {str(e)}")

    async def _process_local_audio_files(self) -> dict:
        # Placeholder implementation
        logger.warning("_process_local_audio_files not implemented")
        raise NotImplementedError("Local audio file processing not implemented")

    async def _process_online_audio_data(self, data: BrevioGenerate, _create_data_result=None, 
                                       current_folder_entry_id: str = "", _user_folder_id: str = "", 
                                       _user_id: str = "") -> dict:
        transcription_sem = asyncio.Semaphore(5)
        summary_sem = asyncio.Semaphore(5)

        async def process_video(index: int, video: MediaEntry):
            try:
                data_result = DataResult()
                destination_path = f"audios/{_user_folder_id}/{current_folder_entry_id}/{index}"
                audio_filename = f"{index}.mp3" if video.url else next(
                    (file for file in listdir(destination_path) if file.endswith(".mp3")), None)

                if not audio_filename:
                    raise FileNotFoundError(f"No MP3 file found in {destination_path}")

                audio_path = path.join(destination_path, audio_filename)
                transcription_path = path.join(destination_path, Constants.TRANSCRIPTION_FILE)
                summary_path = path.join(destination_path, Constants.SUMMARY_FILE)

                logger.info(f"Processing video {index} at {destination_path}")
                self._directory_manager.createFolder(destination_path)

                _file_config = FileConfig(
                    transcription_path=transcription_path,
                    summary_path=summary_path
                )

                if video.url:
                    await self._yt_service.download(video.url, destination_path, str(index))

                if not await self._verify_file_exists(audio_path):
                    raise FileNotFoundError(f"Downloaded file not found: {audio_path}")

                async with transcription_sem:
                    transcription_result = await asyncio.to_thread(
                        self._transcription_service.generate_transcription,
                        audio_path, destination_path, data.prompt_config.language
                    )
                    logger.debug(f"Transcription completed for video {index}")

                torch.cuda.empty_cache()

                async with summary_sem:
                    summary_result = await self._summary_service.generate_summary(
                        prompt_config=data.prompt_config, 
                        file_config=_file_config
                    )
                    logger.debug(f"Summary completed for video {index}")

                torch.cuda.empty_cache()

                data_result.url = str(video.url) if video.url else ""
                data_result.download_location = destination_path
                data_result.index = index

                info = await (self._audio_service.get_media_info_yt(video.url) if video.url 
                            else self._audio_service.get_media_info(audio_path))

                data_result.name = info["title"]
                data_result.duration = float(info["duration"]) if info.get("duration") else 0.0

                if _create_data_result:
                    _create_data_result(_user_id, current_folder_entry_id, data_result)

                return {
                    "transcription": TranscriptionResponse(success=True).__str__(),
                    "summary": SummaryResponse(success=True).__str__()
                }

            except FileNotFoundError as e:
                logger.error(f"File error processing video {index}: {str(e)}")
                raise
            except asyncio.TimeoutError as e:
                logger.error(f"Timeout processing video {index}: {str(e)}")
                raise asyncio.TimeoutError(f"Processing timeout for video {index}: {str(e)}")
            except ValueError as e:
                logger.error(f"Invalid data for video {index}: {str(e)}")
                raise ValueError(f"Invalid data for video {index}: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error processing video {index}: {str(e)}", exc_info=True)
                raise RuntimeError(f"Failed to process video {index}: {str(e)}")

        try:
            tasks = [process_video(index, video) for index, video in enumerate(data.data)]
            results = await asyncio.gather(*tasks)

            return {
                "folder_response": {"success": True, "message": "Directorios creados correctamente"},
                "download_response": {"success": True, "message": "Descargas completadas exitosamente"},
                "transcription_response": [r["transcription"] for r in results],
                "summary_response": [r["summary"] for r in results]
            }
        except Exception as e:
            logger.error(f"Error in online audio processing: {str(e)}", exc_info=True)
            raise

    async def _process_documents(self, _data: BrevioGenerate, _create_data_result=None, 
                               current_folder_entry_id: str = "", _user_folder_id: str = "", 
                               _user_id: str = "") -> dict:
        async def process_task(task):
            try:
                return await task
            except Exception as e:
                logger.error(f"Task failed: {str(e)}", exc_info=True)
                raise

        try:
            tasks = [
                self._process_single_document(
                    index, str(document.path), _data, current_folder_entry_id, 
                    _user_folder_id, _user_id
                ) for index, document in enumerate(_data.data)
            ]
            results = await asyncio.gather(*tasks)

            return {
                "folder_response": {"success": True, "message": "Directorios creados correctamente"},
                "download_response": {"success": True, "message": "Descargas completadas exitosamente"},
                "summary_response": [r["summary"] for r in results]
            }
        except Exception as e:
            logger.error(f"Error processing documents: {str(e)}", exc_info=True)
            raise

    async def _process_single_document(self, index: int, document_path: str, _data: BrevioGenerate, 
                                     current_folder_entry_id: str, _user_folder_id: str, _user_id: str):
        try:
            data_result = DataResult()
            destination_path = f"audios/{_user_folder_id}/{current_folder_entry_id}/{index}"
            summary_path = path.join(destination_path, Constants.SUMMARY_FILE)

            logger.info(f"Processing document {index} at {destination_path}")
            self._directory_manager.createFolder(destination_path)

            _file_config = FileConfig(summary_path=summary_path, document_path=document_path)

            summary_result = await self._summary_service.generate_summary_document(
                _data.prompt_config, _file_config
            )

            data_result.download_location = destination_path
            data_result.index = index

            return {"summary": SummaryResponse(success=True).__str__()}
        except FileNotFoundError as e:
            logger.error(f"File not found for document {index}: {str(e)}")
            raise
        except ValueError as e:
            logger.error(f"Invalid data for document {index}: {str(e)}")
            raise ValueError(f"Invalid document data: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error processing document {index}: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to process document {index}: {str(e)}")

    async def _verify_file_exists(self, file_path: str, max_attempts: int = 10) -> bool:
        try:
            for attempt in range(max_attempts):
                if path.exists(file_path):
                    logger.debug(f"File found: {file_path} on attempt {attempt + 1}")
                    return True
                await asyncio.sleep(0.5)
            logger.error(f"File not found after {max_attempts} attempts: {file_path}")
            raise FileNotFoundError(f"File not found after {max_attempts} attempts: {file_path}")
        except Exception as e:
            logger.error(f"Error verifying file existence {file_path}: {str(e)}", exc_info=True)
            raise Exception(f"Error verifying file existence {file_path}")