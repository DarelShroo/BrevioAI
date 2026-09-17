"""Client IP resolution and FastAPI enforcement helpers (FASE 7)."""

from __future__ import annotations

import ipaddress
import logging
from typing import Optional

from fastapi import Request

from core.brevio_api.models.errors.api_codes import ApiErrorCode, CodedHTTPException
from core.brevio_api.services.anti_abuse.abuse_guard import AbuseGuard
from core.brevio_api.services.anti_abuse.config import (
    BucketConfig,
    anti_abuse_enabled,
    bucket_account_mutation,
    bucket_auth,
    bucket_auth_refresh,
    bucket_estimation,
    bucket_ip_global,
    bucket_job_create,
    bucket_media,
    bucket_upload,
    bucket_youtube,
    rate_limit_enabled,
    trusted_proxy_cidrs,
)
from core.brevio_api.services.anti_abuse.rate_limiter import (
    DistributedRateLimiter,
    RateLimitResult,
)

logger = logging.getLogger(__name__)

_limiter: DistributedRateLimiter | None = None
_guard: AbuseGuard | None = None


def get_limiter() -> DistributedRateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = DistributedRateLimiter()
    return _limiter


def get_guard() -> AbuseGuard:
    global _guard
    if _guard is None:
        _guard = AbuseGuard()
    return _guard


def reset_rate_limiter_for_tests() -> None:
    """Drop shared clients and clear antiabuse keys when Redis is reachable."""
    global _limiter, _guard
    try:
        from core.brevio_api.services.anti_abuse.config import anti_abuse_redis_url
        import redis

        client = redis.Redis.from_url(anti_abuse_redis_url(), decode_responses=True)
        for key in list(client.scan_iter(match="antiabuse:*")):
            client.delete(key)
        client.close()
    except Exception:
        pass
    if _limiter is not None:
        _limiter.close()
    if _guard is not None:
        _guard.close()
    _limiter = None
    _guard = None


def _peer_is_trusted(peer: str) -> bool:
    cidrs = trusted_proxy_cidrs()
    if not cidrs:
        return False
    if "*" in cidrs:
        return True
    try:
        addr = ipaddress.ip_address(peer)
    except ValueError:
        return False
    for item in cidrs:
        try:
            if "/" in item:
                if addr in ipaddress.ip_network(item, strict=False):
                    return True
            elif addr == ipaddress.ip_address(item):
                return True
        except ValueError:
            continue
    return False


def client_ip(request: Request) -> str:
    """Client IP for rate limiting. Forwarded headers only from trusted peers."""
    peer = ""
    if request.client and request.client.host:
        peer = request.client.host
    if peer and _peer_is_trusted(peer):
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip() or peer or "unknown"
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip() or peer or "unknown"
    return peer or "unknown"


def _raise_limited(result: RateLimitResult, *, code: ApiErrorCode = ApiErrorCode.RATE_LIMITED) -> None:
    raise CodedHTTPException(
        status_code=429,
        code=code,
        detail=code.value,
        headers={"Retry-After": str(max(1, result.retry_after))},
    )


def _check_cooldown(subject: str, *, fail_closed: bool) -> None:
    if not anti_abuse_enabled():
        return
    guard = get_guard()
    if fail_closed and not guard.ping():
        raise CodedHTTPException(
            status_code=503,
            code=ApiErrorCode.SCHEDULER_UNAVAILABLE,
            detail=ApiErrorCode.SCHEDULER_UNAVAILABLE.value,
        )
    status = guard.check_cooldown(subject)
    if status.active:
        raise CodedHTTPException(
            status_code=429,
            code=ApiErrorCode.ABUSE_COOLDOWN,
            detail=ApiErrorCode.ABUSE_COOLDOWN.value,
            headers={"Retry-After": str(max(1, status.retry_after))},
        )


def _hit_and_maybe_cooldown(
    *,
    identity: str,
    subject_for_abuse: str,
    bucket: BucketConfig,
    record_abuse: bool = True,
) -> RateLimitResult:
    limiter = get_limiter()
    result = limiter.hit(identity=identity, bucket=bucket)
    if not result.allowed:
        if record_abuse:
            get_guard().record_violation(subject_for_abuse)
        _raise_limited(result)
    return result


def enforce_auth_rate_limit(request: Request, action: str) -> None:
    """Auth endpoints: IP-scoped auth bucket + IP global + cooldown.

    ``refresh`` uses a dedicated higher bucket and does **not** feed the abuse
    cooldown — a dead-session refresh storm must not lock the client out of login.
    """
    if not rate_limit_enabled():
        return
    ip = client_ip(request)
    subject = f"ip:{ip}"
    _check_cooldown(subject, fail_closed=True)

    is_refresh = action == "refresh"
    auth = bucket_auth_refresh() if is_refresh else bucket_auth()
    _hit_and_maybe_cooldown(
        identity=f"ip:{ip}:auth:{action}",
        subject_for_abuse=subject,
        bucket=BucketConfig(
            name=f"auth_{action}",
            limit=auth.limit,
            window_seconds=auth.window_seconds,
            fail_closed=True,
        ),
        record_abuse=not is_refresh,
    )
    _hit_and_maybe_cooldown(
        identity=f"ip:{ip}",
        subject_for_abuse=subject,
        bucket=bucket_ip_global(),
        record_abuse=not is_refresh,
    )


def enforce_expensive_rate_limit(
    request: Request,
    *,
    bucket: BucketConfig,
    user_id: Optional[str] = None,
) -> None:
    """IP + optional user dimensions for costly endpoints."""
    if not rate_limit_enabled():
        return
    ip = client_ip(request)
    abuse_subject = f"user:{user_id}" if user_id else f"ip:{ip}"
    _check_cooldown(abuse_subject, fail_closed=bucket.fail_closed)
    _check_cooldown(f"ip:{ip}", fail_closed=bucket.fail_closed)

    _hit_and_maybe_cooldown(
        identity=f"ip:{ip}",
        subject_for_abuse=f"ip:{ip}",
        bucket=bucket_ip_global(),
    )
    _hit_and_maybe_cooldown(
        identity=f"ip:{ip}",
        subject_for_abuse=f"ip:{ip}",
        bucket=bucket,
    )
    if user_id:
        _hit_and_maybe_cooldown(
            identity=f"user:{user_id}",
            subject_for_abuse=f"user:{user_id}",
            bucket=bucket,
        )


def enforce_job_create_rate_limit(request: Request, user_id: str) -> None:
    enforce_expensive_rate_limit(
        request, bucket=bucket_job_create(), user_id=user_id
    )


def enforce_upload_rate_limit(request: Request, user_id: str) -> None:
    enforce_expensive_rate_limit(request, bucket=bucket_upload(), user_id=user_id)


def enforce_estimation_rate_limit(request: Request, user_id: str) -> None:
    enforce_expensive_rate_limit(
        request, bucket=bucket_estimation(), user_id=user_id
    )


def enforce_youtube_rate_limit(request: Request, user_id: str) -> None:
    enforce_expensive_rate_limit(request, bucket=bucket_youtube(), user_id=user_id)


def enforce_media_rate_limit(request: Request, user_id: str) -> None:
    enforce_expensive_rate_limit(request, bucket=bucket_media(), user_id=user_id)


def enforce_account_mutation_rate_limit(request: Request, user_id: str) -> None:
    enforce_expensive_rate_limit(
        request, bucket=bucket_account_mutation(), user_id=user_id
    )
