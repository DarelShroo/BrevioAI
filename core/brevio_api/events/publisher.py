"""Fire-and-forget publisher used by job persistence, including Celery workers."""

from __future__ import annotations

import logging

from core.brevio_api.events.broker import get_event_broker
from core.brevio_api.events.models import SummaryJobEvent
from core.shared.enums.job_status import JobStatus

logger = logging.getLogger(__name__)


def publish_summary_job_event(
    *,
    user_id: str,
    job_id: str,
    document_id: str,
    status: str,
    document_name: str = "",
    error_code: str | None = None,
    error_message: str | None = None,
) -> SummaryJobEvent | None:
    """Publish a terminal job event. Never raises: job persistence must not fail."""
    if not user_id or not job_id:
        return None
    try:
        if status == JobStatus.COMPLETED.value:
            event = SummaryJobEvent.completed(
                job_id=job_id,
                document_id=str(document_id),
                document_name=document_name or "",
            )
        elif status == JobStatus.FAILED.value:
            event = SummaryJobEvent.failed(
                job_id=job_id,
                document_id=str(document_id),
                document_name=document_name or "",
                error_code=error_code or "FAILED",
                error_message=error_message or "Summary generation failed",
            )
        else:
            return None
        return get_event_broker().publish(str(user_id), event)
    except Exception:
        logger.exception(
            "Failed to publish summary event user=%s job=%s status=%s",
            user_id,
            job_id,
            status,
        )
        return None
