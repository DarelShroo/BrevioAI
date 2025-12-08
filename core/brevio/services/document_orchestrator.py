import asyncio
import logging
import os
from os import path
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from core.brevio.constants.constants import Constants
from core.brevio.managers.directory_manager import DirectoryManager
from core.brevio.models.file_config_model import FileConfig
from core.brevio.models.response_model import SummaryResponse
from core.brevio.services.summary_service import SummaryService
from core.shared.models.brevio.brevio_generate import BrevioGenerate
from core.shared.models.user.data_result import DataResult

logger = logging.getLogger(__name__)

class DocumentOrchestrator:
    def __init__(
        self,
        directory_manager: DirectoryManager,
        summary_service: SummaryService,
    ):
        self._directory_manager = directory_manager
        self._summary_service = summary_service

    async def process_document(
        self,
        index: int,
        document_path: str,
        data: BrevioGenerate,
        current_folder_entry_id: str,
        _user_folder_id: str,
        _user_id: str,
        _create_data_result: Optional[Callable[[str, str, DataResult], Any]] = None,
        _usage_cost_tracker: Optional[Any] = None,
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

            summary_responses = await self._summary_service.generate_summary_documents(
                data.prompt_config, [_file_config]
            )
            
            if not summary_responses or not summary_responses[0].success:
                 error_msg = summary_responses[0].message if summary_responses else "Unknown error"
                 raise RuntimeError(f"Failed to generate summary: {error_msg}")

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
