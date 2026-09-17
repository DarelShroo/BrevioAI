"""FASE 7 anti-abuse / distributed rate-limit configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from core.shared.utils.environment import env_flag, env_int


def anti_abuse_redis_url() -> str:
    from core.shared.utils.redis_url import resolve_redis_url

    return resolve_redis_url(
        os.getenv(
            "ANTI_ABUSE_REDIS_URL",
            os.getenv(
                "CAPACITY_REDIS_URL",
                os.getenv(
                    "JOB_HEARTBEAT_REDIS_URL",
                    os.getenv(
                        "PROVIDER_QUOTA_REDIS_URL",
                        os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/2"),
                    ),
                ),
            ),
        )
    )


def rate_limit_enabled() -> bool:
    return env_flag("RATE_LIMIT_ENABLED", True)


def anti_abuse_enabled() -> bool:
    return env_flag("ANTI_ABUSE_ENABLED", True)


def trusted_proxy_cidrs() -> tuple[str, ...]:
    """Comma-separated CIDRs or IPs that may set X-Forwarded-For / X-Real-IP.

    Empty = never trust forwarded headers (use request.client.host).
    Special value ``*`` trusts any peer (dev only; refused in production).

    Production compose pins ``app_network`` to ``172.28.0.0/16`` (see
    ``docker-compose.yml``) so ``TRUSTED_PROXY=172.28.0.0/16`` matches the
    in-repo nginx→backend topology. External LB/Cloudflare CIDRs are *not*
    inventable from this repo — set them explicitly when that hop exists.
    """
    raw = os.getenv("TRUSTED_PROXY", "").strip()
    if not raw:
        # Dev convenience only when unset. Production must set TRUSTED_PROXY
        # explicitly (assert_secure_runtime_config).
        raw = os.getenv(
            "TRUSTED_PROXY_CIDRS",
            "127.0.0.1/32,::1/128,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16",
        )
    return tuple(p.strip() for p in raw.split(",") if p.strip())


@dataclass(frozen=True)
class BucketConfig:
    name: str
    limit: int
    window_seconds: int
    fail_closed: bool = True  # expensive endpoints fail closed on Redis down


def bucket_auth() -> BucketConfig:
    return BucketConfig(
        "auth",
        max(1, env_int("AUTH_RATE_LIMIT", 10)),
        max(1, env_int("AUTH_RATE_WINDOW_SECONDS", 60)),
        fail_closed=True,
    )


def bucket_auth_refresh() -> BucketConfig:
    """Session keep-alive; higher default than login/register brute-force caps."""
    return BucketConfig(
        "auth_refresh",
        max(1, env_int("AUTH_REFRESH_RATE_LIMIT", 120)),
        max(1, env_int("AUTH_REFRESH_RATE_WINDOW_SECONDS", 60)),
        fail_closed=True,
    )


def bucket_job_create() -> BucketConfig:
    return BucketConfig(
        "job_create",
        max(1, env_int("JOB_CREATE_RATE_LIMIT", 20)),
        max(1, env_int("JOB_CREATE_RATE_WINDOW_SECONDS", 60)),
        fail_closed=True,
    )


def bucket_upload() -> BucketConfig:
    return BucketConfig(
        "upload",
        max(1, env_int("UPLOAD_RATE_LIMIT", 30)),
        max(1, env_int("UPLOAD_RATE_WINDOW_SECONDS", 60)),
        fail_closed=True,
    )


def bucket_estimation() -> BucketConfig:
    return BucketConfig(
        "estimation",
        max(1, env_int("ESTIMATION_RATE_LIMIT", 40)),
        max(1, env_int("ESTIMATION_RATE_WINDOW_SECONDS", 60)),
        fail_closed=True,
    )


def bucket_youtube() -> BucketConfig:
    return BucketConfig(
        "youtube",
        max(1, env_int("YOUTUBE_RATE_LIMIT", 15)),
        max(1, env_int("YOUTUBE_RATE_WINDOW_SECONDS", 60)),
        fail_closed=True,
    )


def bucket_media() -> BucketConfig:
    return BucketConfig(
        "media",
        max(1, env_int("MEDIA_RATE_LIMIT", 20)),
        max(1, env_int("MEDIA_RATE_WINDOW_SECONDS", 60)),
        fail_closed=True,
    )


def bucket_account_mutation() -> BucketConfig:
    return BucketConfig(
        "account_mutation",
        max(1, env_int("ACCOUNT_MUTATION_RATE_LIMIT", 30)),
        max(1, env_int("ACCOUNT_MUTATION_RATE_WINDOW_SECONDS", 60)),
        fail_closed=False,  # reads/mutations lighter; prefer availability
    )


def bucket_ip_global() -> BucketConfig:
    return BucketConfig(
        "ip_global",
        max(1, env_int("IP_GLOBAL_RATE_LIMIT", 120)),
        max(1, env_int("IP_GLOBAL_RATE_WINDOW_SECONDS", 60)),
        fail_closed=True,
    )


def abuse_violation_threshold() -> int:
    return max(1, env_int("ANTI_ABUSE_VIOLATION_THRESHOLD", 20))


def abuse_cooldown_seconds() -> int:
    return max(1, env_int("ANTI_ABUSE_COOLDOWN_SECONDS", 300))


def abuse_violation_ttl_seconds() -> int:
    return max(30, env_int("ANTI_ABUSE_VIOLATION_TTL_SECONDS", 3600))
