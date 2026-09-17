import os

from celery import Celery
from celery.schedules import schedule

from core.brevio_api.services.job_lifecycle import reconcile_interval_seconds
from core.brevio_api.services.capacity.config import scheduler_dispatch_interval_seconds
from core.shared.utils.redis_url import resolve_redis_url

# Celery prefers CELERY_BROKER_URL / CELERY_RESULT_BACKEND from the process
# environment over the Celery(..., broker=...) constructor args. Inject ACL
# credentials into those env vars before the app is created.
_BROKER_URL = resolve_redis_url(
    os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
)
_RESULT_BACKEND = resolve_redis_url(
    os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
)
os.environ["CELERY_BROKER_URL"] = _BROKER_URL
os.environ["CELERY_RESULT_BACKEND"] = _RESULT_BACKEND

celery_app = Celery(
    "worker",
    broker=_BROKER_URL,
    backend=_RESULT_BACKEND,
)
celery_app.conf.broker_url = _BROKER_URL
celery_app.conf.result_backend = _RESULT_BACKEND

# Long-running summary jobs: acknowledge only after success/failure so a killed
# worker redelivers. Prefetch 1 so one worker process does not hoard many jobs.
# Soft/hard time limits remain on the worker CLI (compose): 3600/7200.
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Madrid",
    enable_utc=True,
    CELERYD_FORCE_EXECV=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    beat_schedule={
        "reconcile-stale-jobs": {
            "task": "core.brevio_api.tasks.reconcile_stale_jobs_task",
            "schedule": schedule(run_every=reconcile_interval_seconds()),
        },
        "dispatch-capacity-jobs": {
            "task": "core.brevio_api.tasks.dispatch_capacity_jobs_task",
            "schedule": schedule(run_every=scheduler_dispatch_interval_seconds()),
        },
    },
)

import core.brevio_api.tasks  # noqa: E402,F401
