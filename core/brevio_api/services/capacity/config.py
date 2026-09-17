"""FASE 6 capacity / fair-scheduler configuration (env-backed)."""

from __future__ import annotations

import os

from core.shared.utils.environment import env_int


def capacity_redis_url() -> str:
    from core.shared.utils.redis_url import resolve_redis_url

    return resolve_redis_url(
        os.getenv(
            "CAPACITY_REDIS_URL",
            os.getenv(
                "JOB_HEARTBEAT_REDIS_URL",
                os.getenv(
                    "PROVIDER_QUOTA_REDIS_URL",
                    os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/2"),
                ),
            ),
        )
    )


def global_max_concurrent_jobs() -> int:
    return max(1, env_int("GLOBAL_MAX_CONCURRENT_JOBS", 8))


def global_max_queued_jobs() -> int:
    return max(1, env_int("GLOBAL_MAX_QUEUED_JOBS", 500))


def max_queued_jobs_per_user() -> int:
    """Fallback when plan has no max_queued_jobs field."""
    return max(1, env_int("CAPACITY_MAX_QUEUED_JOBS_PER_USER", 50))


def capacity_lease_ttl_seconds() -> int:
    """Lease TTL; refreshed by job heartbeat. Must exceed heartbeat interval."""
    from core.brevio_api.services.job_lifecycle import heartbeat_ttl_seconds

    floor = heartbeat_ttl_seconds() + 30
    return max(floor, env_int("CAPACITY_LEASE_TTL_SECONDS", 180))


def scheduler_lock_ttl_seconds() -> int:
    return max(5, env_int("SCHEDULER_LOCK_TTL_SECONDS", 15))


def scheduler_dispatch_batch() -> int:
    return max(1, env_int("SCHEDULER_DISPATCH_BATCH", 20))


def scheduler_dispatch_interval_seconds() -> float:
    return float(max(1, env_int("SCHEDULER_DISPATCH_INTERVAL_SECONDS", 2)))


def starvation_age_seconds() -> int:
    """Log/observe QUEUED jobs older than this (no auto-fail)."""
    return max(60, env_int("SCHEDULER_STARVATION_AGE_SECONDS", 900))
