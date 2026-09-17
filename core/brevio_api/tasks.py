import asyncio
import logging
from typing import Any

from asgiref.sync import async_to_sync
from celery import shared_task

from core.brevio_api.services.brevio_service import BrevioService
from core.brevio_api.services.job_lifecycle import JobHeartbeat

logger = logging.getLogger(__name__)


@shared_task(
    name="core.brevio_api.tasks.process_summary_task",
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
)
def process_summary_task(self, job_id: str, **legacy_kwargs: Any) -> dict:
    """Execute a queued summary job by id. Never accepts file bytes.

    ``legacy_kwargs`` absorbs old signatures during rolling deploys; bytes
    payloads are rejected explicitly.
    """
    if "files" in legacy_kwargs and legacy_kwargs["files"] is not None:
        logger.error(
            "event=celery_bytes_payload_rejected job_id=%s",
            job_id or legacy_kwargs.get("folder_entry_id"),
        )
        raise ValueError(
            "process_summary_task no longer accepts file bytes; pass job_id only"
        )

    resolved_job_id = job_id or legacy_kwargs.get("folder_entry_id")
    if not resolved_job_id:
        raise ValueError("job_id is required")

    return async_to_sync(_run_claimed_job)(str(resolved_job_id))


@shared_task(
    name="core.brevio_api.tasks.generate_summary_task",
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
)
def generate_summary_task(self, job_id: str, **legacy_kwargs: Any) -> dict:
    """YouTube/path jobs: transport job_id only (payload lives on FolderEntry)."""
    if "brevio_generate_dict" in legacy_kwargs:
        # Legacy rolling-deploy path: still accept once, but prefer job_id.
        logger.warning(
            "event=legacy_generate_payload_used job_id=%s",
            job_id or "none",
        )
    resolved_job_id = job_id or legacy_kwargs.get("folder_entry_id")
    if not resolved_job_id:
        raise ValueError("job_id is required")
    return async_to_sync(_run_claimed_job)(str(resolved_job_id))


@shared_task(name="core.brevio_api.tasks.reconcile_stale_jobs_task")
def reconcile_stale_jobs_task() -> dict:
    service = BrevioService()
    return async_to_sync(service.reconcile_stale_jobs)()


@shared_task(name="core.brevio_api.tasks.dispatch_capacity_jobs_task")
def dispatch_capacity_jobs_task() -> dict:
    """FASE 6 fair dispatcher tick."""
    service = BrevioService()
    return async_to_sync(service.dispatch_waiting_jobs)()


async def _run_claimed_job(job_id: str) -> dict:
    service = BrevioService()
    claimed = await service.claim_summary_job(job_id)
    if claimed is None:
        return {"status": "ignored", "job_id": job_id, "reason": "not_claimable"}

    heartbeat = JobHeartbeat(job_id)
    heartbeat.start()
    try:
        result = await service.execute_stored_summary_job(job_id)
        return {
            "status": "ok",
            "job_id": job_id,
            "result": result,
        }
    except Exception as exc:
        logger.error(
            "event=job_execution_failed job_id=%s error=%s",
            job_id,
            type(exc).__name__,
            exc_info=True,
        )
        raise
    finally:
        heartbeat.stop()
        try:
            await service.release_capacity_for_job(job_id)
        except Exception:
            logger.exception(
                "event=capacity_release_in_finally_failed job_id=%s", job_id
            )
        # Cancel stray asyncio tasks from nested loops (YouTube path).
        try:
            tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        except Exception:
            pass
