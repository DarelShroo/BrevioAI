import asyncio
import logging
from typing import Any, Callable, Dict, Optional

from core.brevio.managers.directory_manager import DirectoryManager
from core.brevio.services.audio_service import AudioService
from core.brevio.services.document_orchestrator import DocumentOrchestrator
from core.brevio.services.summary_service import SummaryService
from core.brevio.services.transcription_service import TranscriptionService
from core.brevio.services.video_orchestrator import VideoOrchestrator
from core.brevio.services.yt_service import YTService
from core.shared.models.brevio.brevio_generate import BrevioGenerate
from core.shared.models.user.data_result import DataResult
from pydantic import HttpUrl

logger = logging.getLogger(__name__)

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
            
            self._video_orchestrator = VideoOrchestrator(
                self._directory_manager,
                self._summary_service,
                self._transcription_service,
                self._yt_service,
                self._audio_service
            )
            self._document_orchestrator = DocumentOrchestrator(
                self._directory_manager,
                self._summary_service
            )
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
        video: Any,
        data: BrevioGenerate,
        _create_data_result: Callable[[str, str, DataResult], Any],
        current_folder_entry_id: str,
        _user_folder_id: str,
        _user_id: str,
    ) -> Dict[str, str]:
        return await self._video_orchestrator.process_video(
            index, video, data, _create_data_result, current_folder_entry_id, _user_folder_id, _user_id
        )

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
        return await self._document_orchestrator.process_document(
            index, document_path, _data, current_folder_entry_id, _user_folder_id, _user_id, _create_data_result, _usage_cost_tracker
        )
