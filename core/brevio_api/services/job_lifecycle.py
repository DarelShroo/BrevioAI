"""Job lifecycle helpers: heartbeat, claim config, stale detection.

Mongo remains the authority for job status. Redis only answers:
"is a worker still alive for this job?"
"""

from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Optional

from core.shared.utils.environment import env_int

logger = logging.getLogger(__name__)

# Defaults sized for long MAP/REDUCE jobs (up to soft-time-limit 3600s).
# Heartbeat TTL must exceed interval with margin; stale grace must exceed TTL
# so a slow but healthy worker is not killed between beats.
DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 30
DEFAULT_HEARTBEAT_TTL_SECONDS = 120
DEFAULT_STALE_PROCESSING_GRACE_SECONDS = 180
DEFAULT_ORPHAN_QUEUED_SECONDS = 300
DEFAULT_STALE_QUEUED_ENQUEUED_SECONDS = 3600
DEFAULT_RECONCILE_INTERVAL_SECONDS = 60

HEARTBEAT_KEY_PREFIX = "brevio:job:"


def heartbeat_interval_seconds() -> int:
    return max(5, env_int("JOB_HEARTBEAT_INTERVAL_SECONDS", DEFAULT_HEARTBEAT_INTERVAL_SECONDS))


def heartbeat_ttl_seconds() -> int:
    interval = heartbeat_interval_seconds()
    ttl = max(interval * 2, env_int("JOB_HEARTBEAT_TTL_SECONDS", DEFAULT_HEARTBEAT_TTL_SECONDS))
    return ttl


def stale_processing_grace_seconds() -> int:
    """How long after claim (or last Mongo heartbeat) we wait before trusting
    a missing Redis heartbeat as abandonment."""
    floor = heartbeat_ttl_seconds() + 30
    return max(
        floor,
        env_int("JOB_STALE_PROCESSING_GRACE_SECONDS", DEFAULT_STALE_PROCESSING_GRACE_SECONDS),
    )


def orphan_queued_seconds() -> int:
    """QUEUED without successful enqueue — recover or fail after this age."""
    return max(60, env_int("JOB_ORPHAN_QUEUED_SECONDS", DEFAULT_ORPHAN_QUEUED_SECONDS))


def stale_queued_enqueued_seconds() -> int:
    """QUEUED with enqueued_at but never claimed (lost Celery message)."""
    return max(
        120,
        env_int("JOB_STALE_QUEUED_ENQUEUED_SECONDS", DEFAULT_STALE_QUEUED_ENQUEUED_SECONDS),
    )


def reconcile_interval_seconds() -> float:
    return float(
        max(15, env_int("JOB_RECONCILE_INTERVAL_SECONDS", DEFAULT_RECONCILE_INTERVAL_SECONDS))
    )


def heartbeat_redis_url() -> str:
    from core.shared.utils.redis_url import resolve_redis_url

    return resolve_redis_url(
        os.getenv(
            "JOB_HEARTBEAT_REDIS_URL",
            os.getenv(
                "PROVIDER_QUOTA_REDIS_URL",
                os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/2"),
            ),
        )
    )


def heartbeat_key(job_id: str) -> str:
    return f"{HEARTBEAT_KEY_PREFIX}{job_id}:hb"


class JobHeartbeat:
    """Background refresher for Redis heartbeat keys (worker-side, sync redis)."""

    def __init__(self, job_id: str, redis_client: Any | None = None) -> None:
        self.job_id = job_id
        self._client = redis_client
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._owns_client = redis_client is None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        import redis

        self._client = redis.Redis.from_url(
            heartbeat_redis_url(), decode_responses=True
        )
        return self._client

    def touch(self) -> None:
        client = self._get_client()
        client.set(heartbeat_key(self.job_id), "1", ex=heartbeat_ttl_seconds())
        # FASE 6: keep capacity lease alive while the worker is healthy.
        try:
            from core.brevio_api.services.capacity.capacity_store import CapacityStore

            CapacityStore(client).refresh_lease(self.job_id)
        except Exception:
            pass

    def start(self) -> None:
        self.touch()
        logger.info("event=job_heartbeat_started job_id=%s", self.job_id)

        def _loop() -> None:
            while not self._stop.wait(heartbeat_interval_seconds()):
                try:
                    self.touch()
                except Exception as exc:
                    logger.warning(
                        "event=job_heartbeat_refresh_failed job_id=%s error=%s",
                        self.job_id,
                        type(exc).__name__,
                    )

        self._thread = threading.Thread(
            target=_loop, name=f"job-hb-{self.job_id}", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        try:
            client = self._get_client()
            client.delete(heartbeat_key(self.job_id))
        except Exception:
            pass
        if self._owns_client and self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
        logger.info("event=job_heartbeat_stopped job_id=%s", self.job_id)


def heartbeat_alive(job_id: str, redis_client: Any | None = None) -> bool:
    owns = redis_client is None
    client = redis_client
    try:
        if client is None:
            import redis

            client = redis.Redis.from_url(
                heartbeat_redis_url(), decode_responses=True
            )
        return bool(client.exists(heartbeat_key(job_id)))
    except Exception as exc:
        logger.warning(
            "event=job_heartbeat_check_failed job_id=%s error=%s",
            job_id,
            type(exc).__name__,
        )
        # Fail closed for recovery: missing evidence of life → treat as dead
        # only after grace; caller must still apply grace on claimed_at.
        return False
    finally:
        if owns and client is not None:
            try:
                client.close()
            except Exception:
                pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def seconds_since(ts: datetime | None) -> float | None:
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (utcnow() - ts).total_seconds()
