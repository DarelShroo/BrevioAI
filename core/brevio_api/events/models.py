"""Typed contract for user-scoped summary job notifications."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from core.shared.enums.job_status import JobStatus


class SummaryEventType(str, Enum):
    COMPLETED = "summary.completed"
    FAILED = "summary.failed"
    PROGRESS = "summary.progress"


class SummaryEventError(BaseModel):
    code: str
    message: str


class SummaryJobEvent(BaseModel):
    type: SummaryEventType
    job_id: str
    document_id: str
    status: JobStatus
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = ""
    document_name: str = ""
    error: Optional[SummaryEventError] = None
    progress: Optional[int] = None
    global_progress: Optional[int] = None
    stage: Optional[str] = None

    @classmethod
    def create_completed(
        cls,
        *,
        job_id: str,
        document_id: str,
        document_name: str = "",
        event_id: str = "",
    ) -> "SummaryJobEvent":
        return cls(
            type=SummaryEventType.COMPLETED,
            job_id=job_id,
            document_id=document_id,
            status=JobStatus.COMPLETED,
            document_name=document_name,
            event_id=event_id,
        )

    @classmethod
    def create_failed(
        cls,
        *,
        job_id: str,
        document_id: str,
        document_name: str = "",
        error_code: str = "",
        error_message: str = "",
        event_id: str = "",
    ) -> "SummaryJobEvent":
        return cls(
            type=SummaryEventType.FAILED,
            job_id=job_id,
            document_id=document_id,
            status=JobStatus.FAILED,
            document_name=document_name,
            event_id=event_id,
            error=SummaryEventError(
                code=error_code or "FAILED",
                message=error_message or error_code or "SUMMARY_GENERATION_FAILED",
            ),
        )

    @classmethod
    def create_progress(
        cls,
        *,
        job_id: str,
        document_id: str,
        status: JobStatus,
        progress: int,
        stage: str,
        global_progress: Optional[int] = None,
        document_name: str = "",
        event_id: str = "",
    ) -> "SummaryJobEvent":
        return cls(
            type=SummaryEventType.PROGRESS,
            job_id=job_id,
            document_id=document_id,
            status=status,
            progress=progress,
            stage=stage,
            global_progress=global_progress,
            document_name=document_name,
            event_id=event_id,
        )

    completed = create_completed
    failed = create_failed
    progress_event = create_progress
