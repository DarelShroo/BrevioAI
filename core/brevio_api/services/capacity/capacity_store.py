"""Atomic Redis capacity slots (global + per-user) with job leases.

Redis is the operational authority for ephemeral concurrency.
Mongo remains the commercial authority.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from core.brevio_api.services.capacity.config import (
    capacity_lease_ttl_seconds,
    capacity_redis_url,
    global_max_concurrent_jobs,
)

logger = logging.getLogger(__name__)

# KEYS: global_counter, user_counter, lease, global_holders, user_holders
# ARGV: job_id, user_id, global_max, user_max, lease_ttl, holder_payload
ACQUIRE_LUA = """
local gkey = KEYS[1]
local ukey = KEYS[2]
local lease = KEYS[3]
local ghold = KEYS[4]
local uhold = KEYS[5]

local job_id = ARGV[1]
local user_id = ARGV[2]
local gmax = tonumber(ARGV[3])
local umax = tonumber(ARGV[4])
local ttl = tonumber(ARGV[5])
local payload = ARGV[6]

if redis.call('EXISTS', lease) == 1 then
  redis.call('EXPIRE', lease, ttl)
  return {1, 'idempotent', tonumber(redis.call('GET', gkey) or '0'), tonumber(redis.call('GET', ukey) or '0')}
end

local g = tonumber(redis.call('GET', gkey) or '0')
local u = tonumber(redis.call('GET', ukey) or '0')
if g >= gmax then
  return {0, 'CAPACITY_GLOBAL_LIMIT', g, u}
end
if u >= umax then
  return {0, 'CAPACITY_USER_LIMIT', g, u}
end

g = redis.call('INCR', gkey)
u = redis.call('INCR', ukey)
redis.call('SET', lease, payload, 'EX', ttl)
redis.call('SADD', ghold, job_id)
redis.call('SADD', uhold, job_id)
return {1, 'acquired', g, u}
"""

# KEYS: global_counter, user_counter, lease, global_holders, user_holders
# ARGV: job_id, user_id
RELEASE_LUA = """
local gkey = KEYS[1]
local ukey = KEYS[2]
local lease = KEYS[3]
local ghold = KEYS[4]
local uhold = KEYS[5]

local job_id = ARGV[1]
local user_id = ARGV[2]

local held = redis.call('SREM', ghold, job_id)
redis.call('SREM', uhold, job_id)
redis.call('DEL', lease)

if held == 0 then
  local g = tonumber(redis.call('GET', gkey) or '0')
  local u = tonumber(redis.call('GET', ukey) or '0')
  return {0, 'noop', g, u}
end

local g = tonumber(redis.call('GET', gkey) or '0')
if g <= 1 then
  redis.call('SET', gkey, 0)
  g = 0
else
  g = redis.call('DECR', gkey)
end

local u = tonumber(redis.call('GET', ukey) or '0')
if u <= 1 then
  redis.call('SET', ukey, 0)
  u = 0
else
  u = redis.call('DECR', ukey)
end
return {1, 'released', g, u}
"""

REFRESH_LUA = """
local lease = KEYS[1]
local ttl = tonumber(ARGV[1])
if redis.call('EXISTS', lease) == 1 then
  redis.call('EXPIRE', lease, ttl)
  return 1
end
return 0
"""


@dataclass(frozen=True)
class CapacityAcquireResult:
    ok: bool
    reason: str
    global_active: int
    user_active: int


class CapacityStore:
    """Sync Redis client (Celery/worker + dispatcher)."""

    def __init__(self, redis_client: Any | None = None) -> None:
        self._client = redis_client
        self._owns = redis_client is None

    def _get(self) -> Any:
        if self._client is not None:
            return self._client
        import redis

        self._client = redis.Redis.from_url(
            capacity_redis_url(), decode_responses=True
        )
        return self._client

    def close(self) -> None:
        if self._owns and self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    @staticmethod
    def global_key() -> str:
        return "brevio:capacity:global:active"

    @staticmethod
    def user_key(user_id: str) -> str:
        return f"brevio:capacity:user:{user_id}:active"

    @staticmethod
    def lease_key(job_id: str) -> str:
        return f"brevio:capacity:lease:{job_id}"

    @staticmethod
    def global_holders_key() -> str:
        return "brevio:capacity:global:holders"

    @staticmethod
    def user_holders_key(user_id: str) -> str:
        return f"brevio:capacity:user:{user_id}:holders"

    def ping(self) -> bool:
        try:
            return bool(self._get().ping())
        except Exception as exc:
            logger.warning(
                "event=capacity_redis_unavailable error=%s", type(exc).__name__
            )
            return False

    def acquire(
        self,
        *,
        job_id: str,
        user_id: str,
        user_max: int,
        global_max: Optional[int] = None,
        lease_ttl: Optional[int] = None,
    ) -> CapacityAcquireResult:
        gmax = global_max if global_max is not None else global_max_concurrent_jobs()
        ttl = lease_ttl if lease_ttl is not None else capacity_lease_ttl_seconds()
        umax = max(1, int(user_max))
        payload = f"{user_id}|{job_id}"
        try:
            raw = self._get().eval(
                ACQUIRE_LUA,
                5,
                self.global_key(),
                self.user_key(user_id),
                self.lease_key(job_id),
                self.global_holders_key(),
                self.user_holders_key(user_id),
                job_id,
                user_id,
                int(gmax),
                umax,
                int(ttl),
                payload,
            )
        except Exception as exc:
            logger.error(
                "event=capacity_acquire_failed job_id=%s error=%s",
                job_id,
                type(exc).__name__,
            )
            return CapacityAcquireResult(False, "SCHEDULER_UNAVAILABLE", 0, 0)
        ok = int(raw[0]) == 1
        return CapacityAcquireResult(
            ok=ok,
            reason=str(raw[1]),
            global_active=int(raw[2]),
            user_active=int(raw[3]),
        )

    def release(self, *, job_id: str, user_id: str) -> CapacityAcquireResult:
        try:
            raw = self._get().eval(
                RELEASE_LUA,
                5,
                self.global_key(),
                self.user_key(user_id),
                self.lease_key(job_id),
                self.global_holders_key(),
                self.user_holders_key(user_id),
                job_id,
                user_id,
            )
        except Exception as exc:
            logger.error(
                "event=capacity_release_failed job_id=%s error=%s",
                job_id,
                type(exc).__name__,
            )
            return CapacityAcquireResult(False, "SCHEDULER_UNAVAILABLE", 0, 0)
        return CapacityAcquireResult(
            ok=int(raw[0]) == 1,
            reason=str(raw[1]),
            global_active=int(raw[2]),
            user_active=int(raw[3]),
        )

    def refresh_lease(self, job_id: str, lease_ttl: Optional[int] = None) -> bool:
        ttl = lease_ttl if lease_ttl is not None else capacity_lease_ttl_seconds()
        try:
            return int(self._get().eval(REFRESH_LUA, 1, self.lease_key(job_id), int(ttl))) == 1
        except Exception:
            return False

    def has_lease(self, job_id: str) -> bool:
        try:
            return bool(self._get().exists(self.lease_key(job_id)))
        except Exception:
            return False

    def get_lease_user(self, job_id: str) -> Optional[str]:
        try:
            raw = self._get().get(self.lease_key(job_id))
            if not raw:
                return None
            return str(raw).split("|", 1)[0]
        except Exception:
            return None

    def global_active(self) -> int:
        try:
            return int(self._get().get(self.global_key()) or 0)
        except Exception:
            return 0

    def user_active(self, user_id: str) -> int:
        try:
            return int(self._get().get(self.user_key(user_id)) or 0)
        except Exception:
            return 0

    def reclaim_expired_holders(self) -> int:
        """Drop holder set members whose lease key expired (worker crash)."""
        client = self._get()
        released = 0
        try:
            holders = list(client.smembers(self.global_holders_key()) or [])
        except Exception:
            return 0
        for job_id in holders:
            if client.exists(self.lease_key(job_id)):
                continue
            # Lease gone — recover counters via holder membership + best-effort user.
            user_id = None
            # Scan user holder sets is expensive; encode user in a sidecar hash.
            meta = client.get(f"brevio:capacity:lease_meta:{job_id}")
            if meta:
                user_id = str(meta)
            if not user_id:
                client.srem(self.global_holders_key(), job_id)
                # Repair global counter drift
                g = int(client.get(self.global_key()) or 0)
                if g > 0:
                    client.decr(self.global_key())
                released += 1
                continue
            self.release(job_id=job_id, user_id=user_id)
            released += 1
        return released

    def remember_lease_user(self, job_id: str, user_id: str, ttl: Optional[int] = None) -> None:
        ttl = ttl if ttl is not None else capacity_lease_ttl_seconds()
        try:
            self._get().set(
                f"brevio:capacity:lease_meta:{job_id}", user_id, ex=max(ttl * 2, ttl + 60)
            )
        except Exception:
            pass
