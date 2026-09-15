"""Atomic Redis Lua store for provider quota (inflight leases, RPM, TPM, cooldown)."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Optional

from core.brevio.services.provider_quota import keys as keymod
from core.brevio.services.provider_quota.errors import ProviderQuotaUnavailableError

logger = logging.getLogger(__name__)

# KEYS: 1=inflight 2=rpm 3=tpm 4=cooldown 5=degraded
# ARGV:
#  1 lease_id
#  2 lease_ttl_ms
#  3 max_in_flight
#  4 rpm_limit (0 = disabled)
#  5 tpm_limit (0 = disabled)
#  6 reserved_input_tokens
#  7 window_ms (60000)
#  8 degraded_max_in_flight
#
# Returns: {ok, wait_ms, now_ms, expires_at_ms, reason}
# ok=1 granted; ok=0 denied
#
# Circuit after 429: SET degraded=1. Acquire then uses min(max_in_flight,
# degraded_max_in_flight). Success DEL degraded. This is the half-open
# probe — not a separate circuit-breaker library.
ACQUIRE_LUA = """
local inflight = KEYS[1]
local rpm = KEYS[2]
local tpm = KEYS[3]
local cooldown = KEYS[4]
local degraded = KEYS[5]

local lease_id = ARGV[1]
local lease_ttl_ms = tonumber(ARGV[2])
local max_in_flight = tonumber(ARGV[3])
local rpm_limit = tonumber(ARGV[4])
local tpm_limit = tonumber(ARGV[5])
local reserved_input = tonumber(ARGV[6])
local window_ms = tonumber(ARGV[7])
local degraded_max = tonumber(ARGV[8]) or 1

local t = redis.call('TIME')
local now_ms = tonumber(t[1]) * 1000 + math.floor(tonumber(t[2]) / 1000)

local cd = redis.call('GET', cooldown)
if cd then
  local until_ms = tonumber(cd)
  if until_ms and now_ms < until_ms then
    return {0, until_ms - now_ms, now_ms, 0, 'cooldown'}
  end
end

local cap = max_in_flight
if redis.call('GET', degraded) then
  if degraded_max < cap then
    cap = degraded_max
  end
end

-- purge expired leases
redis.call('ZREMRANGEBYSCORE', inflight, '-inf', now_ms)
local active = redis.call('ZCARD', inflight)
if active >= cap then
  return {0, 50, now_ms, 0, 'max_in_flight'}
end

if rpm_limit and rpm_limit > 0 then
  redis.call('ZREMRANGEBYSCORE', rpm, '-inf', now_ms - window_ms)
  local rpm_count = redis.call('ZCARD', rpm)
  if rpm_count >= rpm_limit then
    local oldest = redis.call('ZRANGE', rpm, 0, 0, 'WITHSCORES')
    local wait_ms = 50
    if oldest[2] then
      wait_ms = math.max(50, (tonumber(oldest[2]) + window_ms) - now_ms)
    end
    return {0, wait_ms, now_ms, 0, 'rpm'}
  end
end

if tpm_limit and tpm_limit > 0 and reserved_input > 0 then
  local tokens = tonumber(redis.call('HGET', tpm, 'tokens') or tpm_limit)
  local updated = tonumber(redis.call('HGET', tpm, 'updated_ms') or now_ms)
  local elapsed = now_ms - updated
  if elapsed > 0 then
    local refill = (tpm_limit * elapsed) / window_ms
    tokens = math.min(tpm_limit, tokens + refill)
  end
  if tokens < reserved_input then
    local need = reserved_input - tokens
    local wait_ms = math.max(50, math.ceil((need / tpm_limit) * window_ms))
    redis.call('HSET', tpm, 'tokens', tokens, 'updated_ms', now_ms)
    return {0, wait_ms, now_ms, 0, 'tpm'}
  end
  tokens = tokens - reserved_input
  redis.call('HSET', tpm, 'tokens', tokens, 'updated_ms', now_ms)
elseif tpm_limit and tpm_limit > 0 then
  -- ensure bucket exists
  if redis.call('HLEN', tpm) == 0 then
    redis.call('HSET', tpm, 'tokens', tpm_limit, 'updated_ms', now_ms)
  end
end

local expires_at = now_ms + lease_ttl_ms
redis.call('ZADD', inflight, expires_at, lease_id)
redis.call('PEXPIRE', inflight, lease_ttl_ms)
if rpm_limit and rpm_limit > 0 then
  redis.call('ZADD', rpm, now_ms, lease_id)
end

return {1, 0, now_ms, expires_at, 'ok'}
"""

# KEYS: 1=inflight 2=tpm
# ARGV: 1=lease_id 2=reserved_input 3=actual_prompt_tokens (-1 unknown)
#       4=tpm_limit (0 disabled) 5=allow_refund (1/0) 6=window_ms
RELEASE_LUA = """
local inflight = KEYS[1]
local tpm = KEYS[2]
local lease_id = ARGV[1]
local reserved_input = tonumber(ARGV[2])
local actual_prompt = tonumber(ARGV[3])
local tpm_limit = tonumber(ARGV[4])
local allow_refund = tonumber(ARGV[5])
local window_ms = tonumber(ARGV[6])

local t = redis.call('TIME')
local now_ms = tonumber(t[1]) * 1000 + math.floor(tonumber(t[2]) / 1000)

redis.call('ZREM', inflight, lease_id)

if tpm_limit and tpm_limit > 0 and reserved_input > 0 then
  local tokens = tonumber(redis.call('HGET', tpm, 'tokens') or 0)
  local updated = tonumber(redis.call('HGET', tpm, 'updated_ms') or now_ms)
  local elapsed = now_ms - updated
  if elapsed > 0 then
    local refill = (tpm_limit * elapsed) / window_ms
    tokens = math.min(tpm_limit, tokens + refill)
  end

  if allow_refund == 1 then
    if actual_prompt >= 0 and actual_prompt < reserved_input then
      tokens = math.min(tpm_limit, tokens + (reserved_input - actual_prompt))
    elseif actual_prompt < 0 then
      -- unknown usage after success: do not refund reservation
      tokens = tokens
    elseif actual_prompt > reserved_input then
      local extra = actual_prompt - reserved_input
      tokens = math.max(0, tokens - extra)
    end
  end
  -- allow_refund == 0: keep debit (request may have reached provider)

  redis.call('HSET', tpm, 'tokens', tokens, 'updated_ms', now_ms)
end

return 1
"""

# KEYS: 1=cooldown
# ARGV: 1=new_until_ms
COOLDOWN_LUA = """
local cooldown = KEYS[1]
local new_until = tonumber(ARGV[1])
local current = redis.call('GET', cooldown)
if current then
  local cur = tonumber(current)
  if cur and cur > new_until then
    new_until = cur
  end
end
redis.call('SET', cooldown, new_until)
return new_until
"""


@dataclass
class AcquireResult:
    ok: bool
    lease_id: str
    wait_ms: int
    now_ms: int
    expires_at_ms: int
    reason: str


class RedisQuotaStore:
    def __init__(self, redis_client: Any):
        self._r = redis_client

    async def acquire(
        self,
        *,
        prefix: str,
        max_in_flight: int,
        lease_ttl_ms: int,
        rpm_limit: Optional[int],
        tpm_limit: Optional[int],
        reserved_input_tokens: int,
        lease_id: Optional[str] = None,
        window_ms: int = 60_000,
        degraded_max_in_flight: int = 1,
    ) -> AcquireResult:
        lease_id = lease_id or str(uuid.uuid4())
        try:
            raw = await self._r.eval(
                ACQUIRE_LUA,
                5,
                keymod.inflight_key(prefix),
                keymod.rpm_key(prefix),
                keymod.tpm_key(prefix),
                keymod.cooldown_key(prefix),
                keymod.degraded_key(prefix),
                lease_id,
                str(lease_ttl_ms),
                str(max_in_flight),
                str(rpm_limit or 0),
                str(tpm_limit or 0),
                str(max(0, reserved_input_tokens)),
                str(window_ms),
                str(degraded_max_in_flight),
            )
        except Exception as e:
            logger.error("event=provider_quota_redis_acquire_failed error=%s", e)
            raise ProviderQuotaUnavailableError(f"Redis acquire failed: {e}") from e

        # redis-py may return list of bytes/int
        def _n(x: Any) -> int:
            if isinstance(x, bytes):
                return int(x.decode())
            return int(x)

        def _s(x: Any) -> str:
            if isinstance(x, bytes):
                return x.decode()
            return str(x)

        ok = _n(raw[0]) == 1
        return AcquireResult(
            ok=ok,
            lease_id=lease_id,
            wait_ms=_n(raw[1]),
            now_ms=_n(raw[2]),
            expires_at_ms=_n(raw[3]),
            reason=_s(raw[4]),
        )

    async def release(
        self,
        *,
        prefix: str,
        lease_id: str,
        reserved_input_tokens: int,
        actual_prompt_tokens: Optional[int],
        tpm_limit: Optional[int],
        allow_refund: bool,
        window_ms: int = 60_000,
        call_succeeded: bool = False,
    ) -> None:
        actual = -1 if actual_prompt_tokens is None else int(actual_prompt_tokens)
        try:
            await self._r.eval(
                RELEASE_LUA,
                2,
                keymod.inflight_key(prefix),
                keymod.tpm_key(prefix),
                lease_id,
                str(max(0, reserved_input_tokens)),
                str(actual),
                str(tpm_limit or 0),
                "1" if allow_refund else "0",
                str(window_ms),
            )
        except Exception as e:
            logger.error("event=provider_quota_redis_release_failed error=%s", e)
            raise ProviderQuotaUnavailableError(f"Redis release failed: {e}") from e
        if call_succeeded:
            await self.set_degraded(prefix=prefix, degraded=False)

    async def set_cooldown_until(self, *, prefix: str, until_ms: int) -> int:
        try:
            raw = await self._r.eval(
                COOLDOWN_LUA,
                1,
                keymod.cooldown_key(prefix),
                str(until_ms),
            )
            if isinstance(raw, bytes):
                return int(raw.decode())
            return int(raw)
        except Exception as e:
            logger.error("event=provider_quota_redis_cooldown_failed error=%s", e)
            raise ProviderQuotaUnavailableError(f"Redis cooldown failed: {e}") from e

    async def get_cooldown_remaining_ms(self, *, prefix: str) -> int:
        try:
            t = await self._r.time()
            # redis.asyncio time() returns (seconds, microseconds)
            now_ms = int(t[0]) * 1000 + int(t[1]) // 1000
            cd = await self._r.get(keymod.cooldown_key(prefix))
            if cd is None:
                return 0
            if isinstance(cd, bytes):
                cd = cd.decode()
            until = int(cd)
            return max(0, until - now_ms)
        except Exception as e:
            raise ProviderQuotaUnavailableError(
                f"Redis cooldown read failed: {e}"
            ) from e

    async def set_degraded(self, *, prefix: str, degraded: bool) -> None:
        key = keymod.degraded_key(prefix)
        try:
            if degraded:
                await self._r.set(key, "1")
            else:
                await self._r.delete(key)
        except Exception as e:
            raise ProviderQuotaUnavailableError(
                f"Redis degraded flag failed: {e}"
            ) from e

    async def is_degraded(self, *, prefix: str) -> bool:
        try:
            raw = await self._r.get(keymod.degraded_key(prefix))
            return raw is not None and raw != 0 and raw != b"0"
        except Exception as e:
            raise ProviderQuotaUnavailableError(
                f"Redis degraded read failed: {e}"
            ) from e

    async def ping(self) -> None:
        try:
            pong = await self._r.ping()
            if not pong:
                raise ProviderQuotaUnavailableError("Redis ping failed")
        except ProviderQuotaUnavailableError:
            raise
        except Exception as e:
            raise ProviderQuotaUnavailableError(f"Redis ping failed: {e}") from e
