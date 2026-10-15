import logging
import asyncio
from typing import Dict, Any, Optional

from bson import ObjectId
from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository
from core.brevio_api.events.broker import get_event_broker
from core.brevio_api.events.models import SummaryJobEvent
from core.shared.enums.job_status import JobStatus
from core.shared.models.user.data_result import DataResult

logger = logging.getLogger(__name__)

class ProgressReporter:
    def __init__(self, repo: FolderEntryRepository, user_id: str, job_id: str):
        self.repo = repo
        self.user_id = user_id
        self.job_id = job_id
        # To avoid hammering mongo, we store last persisted progress per item
        self._last_persisted_progress: Dict[str, int] = {}
        self._last_persisted_stage: Dict[str, str] = {}
        # We need the full entry to calculate global progress
        self._lock = asyncio.Lock()

    async def _calculate_global_progress(self, results: list) -> int:
        total_weight = 0
        current_progress = 0
        for item in results:
            weight = getattr(item, "weight", 1) or 1
            progress = getattr(item, "progress", 0) or 0

            if getattr(item, "status", None) == JobStatus.COMPLETED.value:
                progress = 100

            total_weight += weight
            current_progress += (progress * weight)

        if total_weight == 0:
            return 0
        return min(100, max(0, int(current_progress / total_weight)))

    async def update_item_progress(
        self,
        document_id: str,
        result: DataResult,
        *,
        progress: int,
        stage: str,
        status: str = JobStatus.PROCESSING.value,
        force_persist: bool = False
    ) -> None:
        progress = min(100, max(0, int(progress)))
        result.progress = progress
        result.phase = stage
        result.status = status

        async with self._lock:
            try:
                # Fetch fresh to get global state correctly
                entry = await self.repo.get_folder_entry_by_id(self.job_id)
                global_progress = await self._calculate_global_progress(entry.results or [])

                # Check if we should persist to mongo (diff > 5% or stage change)
                last_prog = self._last_persisted_progress.get(document_id, -1)
                last_stage = self._last_persisted_stage.get(document_id, "")

                needs_persist = force_persist or (stage != last_stage) or (abs(progress - last_prog) >= 5)

                if needs_persist:
                    fields = {
                        "progress": progress,
                        "phase": stage,
                        "status": status,
                    }
                    await self.repo.update_data_result(self.job_id, document_id, fields)

                    # Persist global progress
                    await self.repo.update_folder_entry(self.job_id, {"$set": {"progress": global_progress, "stage": stage}})

                    self._last_persisted_progress[document_id] = progress
                    self._last_persisted_stage[document_id] = stage

                # Always emit SSE for smooth frontend
                event = SummaryJobEvent.create_progress(
                    job_id=self.job_id,
                    document_id=document_id,
                    status=JobStatus(status),
                    progress=progress,
                    stage=stage,
                    global_progress=global_progress,
                    document_name=result.name or "",
                )
                get_event_broker().publish(self.user_id, event)
            except Exception as e:
                logger.error(f"Failed to update progress for {document_id}: {e}", exc_info=True)

    async def complete_item(self, document_id: str, result: DataResult) -> None:
        """Mark a document as successfully completed. Explicitly persists success=True
        so it cannot be contradicted by an earlier success=False write."""
        result.success = True
        async with self._lock:
            try:
                entry = await self.repo.get_folder_entry_by_id(self.job_id)
                global_progress = await self._calculate_global_progress(entry.results or [])
                fields = {
                    "progress": 100,
                    "phase": "COMPLETED",
                    "status": JobStatus.COMPLETED.value,
                    "success": True,
                    "error_type": None,
                    "error_code": None,
                    "error_message": None,
                }
                await self.repo.update_data_result(self.job_id, document_id, fields)
                await self.repo.update_folder_entry(
                    self.job_id, {"$set": {"progress": global_progress, "stage": "COMPLETED"}}
                )
                self._last_persisted_progress[document_id] = 100
                self._last_persisted_stage[document_id] = "COMPLETED"
                event = SummaryJobEvent.create_progress(
                    job_id=self.job_id,
                    document_id=document_id,
                    status=JobStatus.COMPLETED,
                    progress=100,
                    stage="COMPLETED",
                    global_progress=global_progress,
                    document_name=result.name or "",
                )
                get_event_broker().publish(self.user_id, event)
            except Exception as e:
                logger.error(f"Failed to complete item {document_id}: {e}", exc_info=True)

    async def fail_item(self, document_id: str, result: DataResult, error: str) -> None:
        """Mark a document as failed. Explicitly persists success=False and the error reason."""
        current_progress = min(100, max(0, int(result.progress or 0)))
        result.success = False
        async with self._lock:
            try:
                entry = await self.repo.get_folder_entry_by_id(self.job_id)
                global_progress = await self._calculate_global_progress(entry.results or [])
                fields = {
                    "progress": current_progress,
                    "phase": "FAILED",
                    "status": JobStatus.FAILED.value,
                    "success": False,
                    "error_message": error,
                    "error_code": getattr(result, "error_code", None) or "SUMMARY_GENERATION_FAILED",
                    "error_type": getattr(result, "error_type", None) or "SummaryError",
                }
                await self.repo.update_data_result(self.job_id, document_id, fields)
                await self.repo.update_folder_entry(
                    self.job_id, {"$set": {"progress": global_progress, "stage": "FAILED"}}
                )
                self._last_persisted_progress[document_id] = current_progress
                self._last_persisted_stage[document_id] = "FAILED"
                event = SummaryJobEvent.create_failed(
                    job_id=self.job_id,
                    document_id=document_id,
                    document_name=result.name or "",
                    error_code=fields["error_code"],
                    error_message=error,
                )
                get_event_broker().publish(self.user_id, event)
            except Exception as e:
                logger.error(f"Failed to mark item {document_id} as failed: {e}", exc_info=True)

