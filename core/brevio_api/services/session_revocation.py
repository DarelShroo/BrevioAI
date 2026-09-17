"""Short-lived Redis denylist for access JWTs (FASE 8).

Logout / password-change must invalidate access cookies that would otherwise
remain valid until exp. Keys expire with the access-token TTL — no permanent
session store.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from core.brevio_api.services.anti_abuse.config import anti_abuse_redis_url
from core.shared.utils.environment import access_token_expire_minutes

logger = logging.getLogger(__name__)

_PREFIX_JTI = "auth:deny:jti:"
_PREFIX_USER = "auth:deny:user:"


def _client():
    import redis

    return redis.Redis.from_url(anti_abuse_redis_url(), decode_responses=True)


def access_ttl_seconds() -> int:
    return max(60, int(access_token_expire_minutes()) * 60)


def deny_access_jti(jti: str, *, ttl_seconds: Optional[int] = None) -> None:
    if not jti:
        return
    ttl = ttl_seconds if ttl_seconds is not None else access_ttl_seconds()
    try:
        _client().set(f"{_PREFIX_JTI}{jti}", "1", ex=max(1, ttl))
    except Exception:
        logger.warning("event=access_jti_deny_failed jti_prefix=%s", jti[:8], exc_info=True)


def deny_user_access(user_id: str, *, ttl_seconds: Optional[int] = None) -> None:
    """Invalidate all access tokens for user issued at or before now (epoch)."""
    if not user_id:
        return
    ttl = ttl_seconds if ttl_seconds is not None else access_ttl_seconds()
    try:
        _client().set(
            f"{_PREFIX_USER}{user_id}", str(int(time.time())), ex=max(1, ttl)
        )
    except Exception:
        logger.warning(
            "event=access_user_deny_failed user_id=%s", user_id, exc_info=True
        )


def is_access_revoked(payload: dict) -> bool:
    """Return True if access token jti/user was denied after logout/password change."""
    jti = str(payload.get("jti") or "")
    user_id = str(payload.get("id") or "")
    try:
        client = _client()
        if jti and client.exists(f"{_PREFIX_JTI}{jti}"):
            return True
        if user_id:
            raw = client.get(f"{_PREFIX_USER}{user_id}")
            if raw is not None:
                try:
                    epoch = int(raw)
                except (TypeError, ValueError):
                    return True
                iat = payload.get("iat")
                if iat is None:
                    return True
                try:
                    return float(iat) <= float(epoch)
                except (TypeError, ValueError):
                    return True
        return False
    except Exception:
        # Fail open for reads: Redis outage must not lock out all sessions.
        # Logout still revoked refresh family in Mongo.
        logger.warning("event=access_revoke_check_failed", exc_info=True)
        return False
