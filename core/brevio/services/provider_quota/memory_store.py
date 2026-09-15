"""In-memory quota store with the same acquire/release/cooldown contract as Redis.

Used by tests to simulate multiple workers sharing one backend without Redis.
Not a production substitute: Celery workers need RedisQuotaStore.
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Optional

from core.brevio.services.provider_quota.redis_store import AcquireResult


class InMemoryQuotaStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._inflight: dict[str, dict[str, int]] = {}
        self._rpm: dict[str, dict[str, int]] = {}
        self._tpm: dict[str, dict[str, float]] = {}
        self._cooldown: dict[str, int] = {}
        self._degraded: dict[str, bool] = {}

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    def _purge_inflight(self, prefix: str, now_ms: int) -> None:
        leases = self._inflight.setdefault(prefix, {})
        expired = [lid for lid, exp in leases.items() if exp <= now_ms]
        for lid in expired:
            leases.pop(lid, None)

    def _purge_rpm(self, prefix: str, now_ms: int, window_ms: int) -> None:
        stamps = self._rpm.setdefault(prefix, {})
        expired = [lid for lid, ts in stamps.items() if ts <= now_ms - window_ms]
        for lid in expired:
            stamps.pop(lid, None)

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
        with self._lock:
            now_ms = self._now_ms()
            until = self._cooldown.get(prefix, 0)
            if until > now_ms:
                return AcquireResult(
                    ok=False,
                    lease_id=lease_id,
                    wait_ms=until - now_ms,
                    now_ms=now_ms,
                    expires_at_ms=0,
                    reason="cooldown",
                )

            self._purge_inflight(prefix, now_ms)
            cap = max_in_flight
            if self._degraded.get(prefix):
                cap = min(cap, max(1, degraded_max_in_flight))
            active = len(self._inflight.setdefault(prefix, {}))
            if active >= cap:
                return AcquireResult(
                    ok=False,
                    lease_id=lease_id,
                    wait_ms=50,
                    now_ms=now_ms,
                    expires_at_ms=0,
                    reason="max_in_flight",
                )

            if rpm_limit and rpm_limit > 0:
                self._purge_rpm(prefix, now_ms, window_ms)
                rpm = self._rpm.setdefault(prefix, {})
                if len(rpm) >= rpm_limit:
                    oldest = min(rpm.values()) if rpm else now_ms
                    wait_ms = max(50, (oldest + window_ms) - now_ms)
                    return AcquireResult(
                        ok=False,
                        lease_id=lease_id,
                        wait_ms=wait_ms,
                        now_ms=now_ms,
                        expires_at_ms=0,
                        reason="rpm",
                    )

            if tpm_limit and tpm_limit > 0 and reserved_input_tokens > 0:
                bucket = self._tpm.setdefault(
                    prefix, {"tokens": float(tpm_limit), "updated_ms": float(now_ms)}
                )
                elapsed = now_ms - bucket["updated_ms"]
                if elapsed > 0:
                    bucket["tokens"] = min(
                        float(tpm_limit),
                        bucket["tokens"] + (tpm_limit * elapsed) / window_ms,
                    )
                    bucket["updated_ms"] = float(now_ms)
                if bucket["tokens"] < reserved_input_tokens:
                    need = reserved_input_tokens - bucket["tokens"]
                    wait_ms = max(50, int((need / tpm_limit) * window_ms))
                    return AcquireResult(
                        ok=False,
                        lease_id=lease_id,
                        wait_ms=wait_ms,
                        now_ms=now_ms,
                        expires_at_ms=0,
                        reason="tpm",
                    )
                bucket["tokens"] -= reserved_input_tokens
                bucket["updated_ms"] = float(now_ms)

            expires_at = now_ms + lease_ttl_ms
            self._inflight.setdefault(prefix, {})[lease_id] = expires_at
            if rpm_limit and rpm_limit > 0:
                self._rpm.setdefault(prefix, {})[lease_id] = now_ms
            return AcquireResult(
                ok=True,
                lease_id=lease_id,
                wait_ms=0,
                now_ms=now_ms,
                expires_at_ms=expires_at,
                reason="ok",
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
        with self._lock:
            self._inflight.setdefault(prefix, {}).pop(lease_id, None)
            if call_succeeded:
                self._degraded[prefix] = False
            if (
                tpm_limit
                and tpm_limit > 0
                and reserved_input_tokens > 0
                and allow_refund
            ):
                now_ms = self._now_ms()
                bucket = self._tpm.setdefault(
                    prefix, {"tokens": 0.0, "updated_ms": float(now_ms)}
                )
                if (
                    actual_prompt_tokens is not None
                    and actual_prompt_tokens < reserved_input_tokens
                ):
                    bucket["tokens"] = min(
                        float(tpm_limit),
                        bucket["tokens"]
                        + (reserved_input_tokens - actual_prompt_tokens),
                    )

    async def set_cooldown_until(self, *, prefix: str, until_ms: int) -> int:
        with self._lock:
            current = self._cooldown.get(prefix, 0)
            new_until = max(current, int(until_ms))
            self._cooldown[prefix] = new_until
            return new_until

    async def get_cooldown_remaining_ms(self, *, prefix: str) -> int:
        with self._lock:
            now_ms = self._now_ms()
            return max(0, self._cooldown.get(prefix, 0) - now_ms)

    async def set_degraded(self, *, prefix: str, degraded: bool) -> None:
        with self._lock:
            self._degraded[prefix] = bool(degraded)

    async def is_degraded(self, *, prefix: str) -> bool:
        with self._lock:
            return bool(self._degraded.get(prefix))

    async def ping(self) -> None:
        return None
