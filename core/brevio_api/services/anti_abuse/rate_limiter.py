"""Distributed Redis fixed-window rate limiter (FASE 7).

Atomic check+increment via Lua. Multi-replica safe.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

from core.brevio_api.services.anti_abuse.config import (
    BucketConfig,
    anti_abuse_redis_url,
    rate_limit_enabled,
)

logger = logging.getLogger(__name__)

# KEYS[1] = counter key
# ARGV[1] = limit, ARGV[2] = window_seconds
# Returns: {allowed(0/1), count, limit, ttl_ms, retry_after_s}
HIT_LUA = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local n = redis.call('INCR', key)
if n == 1 then
  redis.call('EXPIRE', key, window)
end
local ttl = redis.call('PTTL', key)
if ttl < 0 then
  redis.call('EXPIRE', key, window)
  ttl = window * 1000
end
local retry = math.ceil(ttl / 1000)
if n > limit then
  return {0, n, limit, ttl, retry}
end
return {1, n, limit, ttl, retry}
"""


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int
    reset_at: float
    bucket: str
    key: str


class DistributedRateLimiter:
    def __init__(self, redis_client: Any | None = None) -> None:
        self._client = redis_client
        self._owns = redis_client is None

    def _get(self) -> Any:
        if self._client is not None:
            return self._client
        import redis

        self._client = redis.Redis.from_url(
            anti_abuse_redis_url(), decode_responses=True
        )
        return self._client

    def close(self) -> None:
        if self._owns and self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    def ping(self) -> bool:
        try:
            return bool(self._get().ping())
        except Exception as exc:
            logger.warning(
                "event=rate_limit_redis_unavailable error=%s", type(exc).__name__
            )
            return False

    def hit(self, *, identity: str, bucket: BucketConfig) -> RateLimitResult:
        """Atomic fixed-window hit. identity e.g. ``ip:1.2.3.4`` or ``user:abc``."""
        key = f"antiabuse:rl:{identity}:{bucket.name}"
        if not rate_limit_enabled():
            return RateLimitResult(
                True, bucket.limit, bucket.limit, 0, time.time() + bucket.window_seconds, bucket.name, key
            )
        try:
            raw = self._get().eval(
                HIT_LUA, 1, key, int(bucket.limit), int(bucket.window_seconds)
            )
        except Exception as exc:
            logger.error(
                "event=rate_limit_eval_failed bucket=%s error=%s",
                bucket.name,
                type(exc).__name__,
            )
            if bucket.fail_closed:
                return RateLimitResult(
                    False,
                    bucket.limit,
                    0,
                    max(1, bucket.window_seconds),
                    time.time() + bucket.window_seconds,
                    bucket.name,
                    key,
                )
            return RateLimitResult(
                True,
                bucket.limit,
                bucket.limit,
                0,
                time.time() + bucket.window_seconds,
                bucket.name,
                key,
            )
        allowed = int(raw[0]) == 1
        count = int(raw[1])
        limit = int(raw[2])
        ttl_ms = max(0, int(raw[3]))
        retry = max(1, int(raw[4])) if not allowed else 0
        remaining = max(0, limit - count) if allowed else 0
        reset_at = time.time() + (ttl_ms / 1000.0)
        if not allowed:
            logger.info(
                "event=rate_limit_hit bucket=%s key=%s count=%s limit=%s retry_after=%s",
                bucket.name,
                key,
                count,
                limit,
                retry,
            )
        return RateLimitResult(
            allowed=allowed,
            limit=limit,
            remaining=remaining,
            retry_after=retry,
            reset_at=reset_at,
            bucket=bucket.name,
            key=key,
        )
