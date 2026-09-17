"""ProviderQuotaManager: distributed acquire/release/cooldown.

Circuit-breaker decision
------------------------
A separate CB library is not added. Redis cooldown after 429 already opens
the circuit for every worker sharing the quota. After cooldown, the Redis
`degraded` flag keeps max_in_flight at degraded_max_in_flight (default 1)
until a successful call clears it (half-open probe). Combined with RPM
in the Lua/in-memory acquire, this is the resume control — not uncoordinated
sleep() jitter as the authority.

max_in_flight semantics
-----------------------
max_in_flight caps ACTIVE provider ops, not waiting tasks. Waiters for
capacity (reason=max_in_flight) form a queue and must acquire when a slot
frees. acquire_timeout_ms applies to rate/cooldown/TPM denials, not to
ordinary capacity queue waits.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import time
from collections import deque
from typing import Any, Optional

import redis.asyncio as redis_async

from core.brevio.services.provider_quota.errors import (
    ProviderQuotaUnavailableError,
    QuotaAcquireTimeoutError,
    QuotaPolicyMissingError,
)
from core.brevio.services.provider_quota.keys import build_quota_scope_id, redis_prefix
from core.brevio.services.provider_quota.metrics import ProviderCallMetrics
from core.brevio.services.provider_quota.policy import (
    QuotaPolicy,
    QuotaPolicyRegistry,
    effective_rpm,
    provider_quota_enabled,
)
from core.brevio.services.provider_quota.redis_store import (
    AcquireResult,
    RedisQuotaStore,
)

logger = logging.getLogger(__name__)

# Deny reasons that mean "wait for capacity" — queue, do not fail on acquire_timeout.
_CAPACITY_QUEUE_REASONS = frozenset({"max_in_flight"})


class _LocalPacingState:
    """In-process backstop. Redis (when enabled) is the global authority.

    Always honors policy.max_in_flight (not only after 429). After a 429,
    degraded=True additionally caps inflight at degraded_max_in_flight.
    When quota Redis is disabled, a local RPM window is also enforced so a
    single worker cannot dump max_concurrent_chunks into the provider at once.
    Multi-worker protection still requires PROVIDER_QUOTA_ENABLED + Redis.
    """

    def __init__(self) -> None:
        self.cooldown_until = 0.0
        self.inflight = 0
        self.waiting = 0
        self.degraded = False
        self.rpm_times: deque[float] = deque()
        self.cond = asyncio.Condition()


class ProviderQuotaManager:
    def __init__(
        self,
        store: Optional[Any] = None,
        registry: Optional[QuotaPolicyRegistry] = None,
        redis_url: Optional[str] = None,
        metrics: Optional[ProviderCallMetrics] = None,
    ):
        self._store = store
        self._registry = registry
        from core.shared.utils.redis_url import resolve_redis_url

        self._redis_url = resolve_redis_url(
            redis_url
            or os.getenv(
                "PROVIDER_QUOTA_REDIS_URL",
                os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/2"),
            )
        )
        self._client: Any = None
        self._pacing: dict[tuple[str, str, str], _LocalPacingState] = {}
        self.metrics = metrics or ProviderCallMetrics()

    def _pace(
        self, provider: str, model: str, quota_scope_id: str
    ) -> _LocalPacingState:
        key = (provider.lower(), model, quota_scope_id)
        state = self._pacing.get(key)
        if state is None:
            state = _LocalPacingState()
            self._pacing[key] = state
        return state

    def _prefix(
        self, provider: str, quota_scope_id: str, model: str, policy: QuotaPolicy
    ) -> str:
        return redis_prefix(
            provider, quota_scope_id, model, quota_group=policy.quota_group
        )

    def _active_count(self, provider: str, model: str, quota_scope_id: str) -> int:
        return self._pace(provider, model, quota_scope_id).inflight

    def _waiting_count(self, provider: str, model: str, quota_scope_id: str) -> int:
        return self._pace(provider, model, quota_scope_id).waiting

    def _inflight_cap(
        self, provider: str, model: str, quota_scope_id: str, policy: QuotaPolicy
    ) -> int:
        state = self._pace(provider, model, quota_scope_id)
        if state.degraded:
            return min(policy.max_in_flight, policy.degraded_max_in_flight)
        return policy.max_in_flight

    def _log_quota(
        self,
        action: str,
        *,
        provider: str,
        model: str,
        phase: str,
        retry_number: int,
        chunk_id: Optional[str],
        lease_id: Optional[str],
        inflight: int,
        inflight_cap: int,
        waiting: int,
        wait_ms: Optional[float] = None,
        reason: Optional[str] = None,
        acquired_at: Optional[float] = None,
        released_at: Optional[float] = None,
    ) -> None:
        parts = [
            f"[QUOTA] {action}",
            f"provider={provider}",
            f"model={model}",
            f"phase={phase}",
            f"chunk={chunk_id or '-'}",
            f"lease_id={lease_id or '-'}",
            f"inflight={inflight}",
            f"inflight_cap={inflight_cap}",
            f"waiting={waiting}",
            f"retry={retry_number}",
        ]
        if reason is not None:
            parts.append(f"reason={reason}")
        if wait_ms is not None:
            parts.append(f"wait_ms={wait_ms:.0f}")
        if acquired_at is not None:
            parts.append(f"acquired_at={acquired_at:.3f}")
        if released_at is not None:
            parts.append(f"released_at={released_at:.3f}")
        logger.info(" ".join(parts))

    async def _acquire_local_slot(
        self,
        provider: str,
        model: str,
        quota_scope_id: str,
        policy: QuotaPolicy,
        *,
        enforce_local_rpm: bool,
        phase: str = "UNKNOWN",
        retry_number: int = 0,
        chunk_id: Optional[str] = None,
    ) -> None:
        state = self._pace(provider, model, quota_scope_id)
        rpm_cap = effective_rpm(policy) if enforce_local_rpm else None
        wait_log_at = 0.0
        queued = False
        async with state.cond:
            try:
                while True:
                    now = time.monotonic()
                    cooldown_left = state.cooldown_until - now
                    if cooldown_left > 0:
                        if not queued:
                            state.waiting += 1
                            queued = True
                        if now - wait_log_at >= 5.0:
                            self._log_quota(
                                "WAIT",
                                provider=provider,
                                model=model,
                                phase=phase,
                                retry_number=retry_number,
                                chunk_id=chunk_id,
                                lease_id=None,
                                inflight=state.inflight,
                                inflight_cap=(
                                    min(
                                        policy.max_in_flight,
                                        policy.degraded_max_in_flight,
                                    )
                                    if state.degraded
                                    else policy.max_in_flight
                                ),
                                waiting=state.waiting,
                                reason="cooldown",
                                wait_ms=cooldown_left * 1000.0,
                            )
                            wait_log_at = now
                        try:
                            await asyncio.wait_for(
                                state.cond.wait(),
                                timeout=min(cooldown_left, 1.0),
                            )
                        except TimeoutError:
                            pass
                        continue
                    inflight_cap = (
                        min(policy.max_in_flight, policy.degraded_max_in_flight)
                        if state.degraded
                        else policy.max_in_flight
                    )
                    if inflight_cap is not None and state.inflight >= inflight_cap:
                        if not queued:
                            state.waiting += 1
                            queued = True
                        if now - wait_log_at >= 5.0:
                            self._log_quota(
                                "WAIT",
                                provider=provider,
                                model=model,
                                phase=phase,
                                retry_number=retry_number,
                                chunk_id=chunk_id,
                                lease_id=None,
                                inflight=state.inflight,
                                inflight_cap=inflight_cap,
                                waiting=state.waiting,
                                reason="max_in_flight",
                            )
                            wait_log_at = now
                        await state.cond.wait()
                        continue
                    if rpm_cap:
                        window_start = now - 60.0
                        while state.rpm_times and state.rpm_times[0] < window_start:
                            state.rpm_times.popleft()
                        if len(state.rpm_times) >= rpm_cap:
                            if not queued:
                                state.waiting += 1
                                queued = True
                            if now - wait_log_at >= 5.0:
                                self._log_quota(
                                    "WAIT",
                                    provider=provider,
                                    model=model,
                                    phase=phase,
                                    retry_number=retry_number,
                                    chunk_id=chunk_id,
                                    lease_id=None,
                                    inflight=state.inflight,
                                    inflight_cap=inflight_cap,
                                    waiting=state.waiting,
                                    reason="rpm",
                                )
                                wait_log_at = now
                            oldest = state.rpm_times[0]
                            wait = min(max(oldest + 60.0 - now, 0.05), 1.0)
                            try:
                                await asyncio.wait_for(state.cond.wait(), timeout=wait)
                            except TimeoutError:
                                pass
                            continue
                        state.rpm_times.append(now)
                    state.inflight += 1
                    return
            finally:
                if queued:
                    state.waiting = max(0, state.waiting - 1)

    async def _release_local_slot(
        self,
        provider: str,
        model: str,
        quota_scope_id: str,
        *,
        success: bool,
    ) -> None:
        state = self._pace(provider, model, quota_scope_id)
        async with state.cond:
            state.inflight = max(0, state.inflight - 1)
            if success:
                state.degraded = False
            state.cond.notify_all()

    @property
    def enabled(self) -> bool:
        return provider_quota_enabled()

    async def _ensure_store(self) -> Any:
        if self._store is not None:
            return self._store
        try:
            self._client = redis_async.from_url(self._redis_url, decode_responses=False)
            store = RedisQuotaStore(self._client)
            await store.ping()
            self._store = store
            return store
        except Exception as e:
            raise ProviderQuotaUnavailableError(
                f"Cannot connect to quota Redis: {e}"
            ) from e

    def _registry_or_load(self) -> QuotaPolicyRegistry:
        if self._registry is not None:
            return self._registry
        self._registry = QuotaPolicyRegistry.from_env()
        return self._registry

    def resolve_policy(
        self, provider: str, model: str, quota_scope_id: str
    ) -> QuotaPolicy:
        require = self.enabled
        return self._registry_or_load().resolve(
            provider, model, require=require, quota_scope_id=quota_scope_id
        )

    def resolve_scope(
        self,
        *,
        is_platform: bool,
        credential_id: str,
        provider: str,
        model: str,
    ) -> str:
        try:
            reg = self._registry_or_load()
            for p in reg._policies:
                if (
                    p.provider == provider.lower()
                    and (p.model == model or p.model == "*")
                    and p.quota_scope
                ):
                    return build_quota_scope_id(
                        is_platform=is_platform,
                        credential_id=credential_id,
                        policy_scope=p.quota_scope,
                    )
        except QuotaPolicyMissingError:
            pass
        return build_quota_scope_id(
            is_platform=is_platform, credential_id=credential_id
        )

    async def acquire(
        self,
        *,
        provider: str,
        model: str,
        quota_scope_id: str,
        estimated_input_tokens: int,
        policy: Optional[QuotaPolicy] = None,
        phase: str = "UNKNOWN",
        retry_number: int = 0,
        chunk_id: Optional[str] = None,
    ) -> tuple[str, QuotaPolicy, AcquireResult]:
        """
        Block until lease granted or timeout on non-capacity denials.

        max_in_flight denials queue until a slot frees (no acquire_timeout fail).
        rpm/tpm/cooldown denials honor acquire_timeout_ms as a safety bound.
        When quota disabled, still applies local inflight + RPM from policy
        (per-process backstop). Redis is the global authority when enabled.
        """
        policy = policy or self.resolve_policy(provider, model, quota_scope_id)
        wait_started = time.monotonic()
        remote_waiting = False
        await self._acquire_local_slot(
            provider,
            model,
            quota_scope_id,
            policy,
            enforce_local_rpm=not self.enabled,
            phase=phase,
            retry_number=retry_number,
            chunk_id=chunk_id,
        )
        try:
            if not self.enabled:
                lease_id = f"local-{time.time_ns()}"
                acquired_at = time.time()
                wait_ms = (time.monotonic() - wait_started) * 1000.0
                self._log_quota(
                    "ACQUIRE",
                    provider=provider,
                    model=model,
                    phase=phase,
                    retry_number=retry_number,
                    chunk_id=chunk_id,
                    lease_id=lease_id,
                    inflight=self._active_count(provider, model, quota_scope_id),
                    inflight_cap=self._inflight_cap(
                        provider, model, quota_scope_id, policy
                    ),
                    waiting=self._waiting_count(provider, model, quota_scope_id),
                    wait_ms=wait_ms,
                    acquired_at=acquired_at,
                )
                return (
                    lease_id,
                    policy,
                    AcquireResult(
                        ok=True,
                        lease_id=lease_id,
                        wait_ms=int(wait_ms),
                        now_ms=int(time.time() * 1000),
                        expires_at_ms=int(time.time() * 1000) + policy.lease_ttl_ms,
                        reason="quota_disabled",
                    ),
                )

            store = await self._ensure_store()
            prefix = self._prefix(provider, quota_scope_id, model, policy)
            # Safety deadline for rate/cooldown/TPM only — not capacity queue.
            rate_deadline = time.monotonic() + (policy.acquire_timeout_ms / 1000.0)
            last: Optional[AcquireResult] = None
            rpm_limit = effective_rpm(policy)
            wait_log_at = 0.0
            while True:
                acquire_kwargs = dict(
                    prefix=prefix,
                    max_in_flight=policy.max_in_flight,
                    lease_ttl_ms=policy.lease_ttl_ms,
                    rpm_limit=rpm_limit,
                    tpm_limit=policy.tpm,
                    reserved_input_tokens=estimated_input_tokens,
                    degraded_max_in_flight=policy.degraded_max_in_flight,
                )
                try:
                    last = await store.acquire(**acquire_kwargs)
                except TypeError:
                    acquire_kwargs.pop("degraded_max_in_flight", None)
                    last = await store.acquire(**acquire_kwargs)
                if last.ok:
                    if remote_waiting:
                        state = self._pace(provider, model, quota_scope_id)
                        async with state.cond:
                            state.waiting = max(0, state.waiting - 1)
                        remote_waiting = False
                    acquired_at = time.time()
                    wait_ms = (time.monotonic() - wait_started) * 1000.0
                    self._log_quota(
                        "ACQUIRE",
                        provider=provider,
                        model=model,
                        phase=phase,
                        retry_number=retry_number,
                        chunk_id=chunk_id,
                        lease_id=last.lease_id,
                        inflight=self._active_count(provider, model, quota_scope_id),
                        inflight_cap=self._inflight_cap(
                            provider, model, quota_scope_id, policy
                        ),
                        waiting=self._waiting_count(provider, model, quota_scope_id),
                        wait_ms=wait_ms,
                        acquired_at=acquired_at,
                    )
                    return last.lease_id, policy, last

                reason = last.reason or "unknown"
                now_mono = time.monotonic()
                is_capacity = reason in _CAPACITY_QUEUE_REASONS
                if not is_capacity and now_mono >= rate_deadline:
                    last_reason = reason
                    raise QuotaAcquireTimeoutError(
                        f"Timed out acquiring provider quota lease "
                        f"(last_reason={last_reason})",
                        last_reason=last_reason,
                        provider=provider,
                        model=model,
                        max_in_flight=policy.max_in_flight,
                    )

                if is_capacity and not remote_waiting:
                    state = self._pace(provider, model, quota_scope_id)
                    async with state.cond:
                        state.waiting += 1
                    remote_waiting = True

                if now_mono - wait_log_at >= 5.0:
                    self._log_quota(
                        "WAIT",
                        provider=provider,
                        model=model,
                        phase=phase,
                        retry_number=retry_number,
                        chunk_id=chunk_id,
                        lease_id=None,
                        inflight=self._active_count(provider, model, quota_scope_id),
                        inflight_cap=self._inflight_cap(
                            provider, model, quota_scope_id, policy
                        ),
                        waiting=self._waiting_count(provider, model, quota_scope_id),
                        reason=reason,
                        wait_ms=float(last.wait_ms),
                    )
                    wait_log_at = now_mono

                wait_s = min(max(last.wait_ms / 1000.0, 0.05), 5.0)
                jitter = wait_s * policy.jitter_ratio * random.random()
                sleep_s = min(wait_s + jitter, 5.0)
                self.metrics.record_wait(sleep_s)
                await asyncio.sleep(sleep_s)
        except BaseException:
            if remote_waiting:
                state = self._pace(provider, model, quota_scope_id)
                async with state.cond:
                    state.waiting = max(0, state.waiting - 1)
            await self._release_local_slot(
                provider, model, quota_scope_id, success=False
            )
            raise

    async def release(
        self,
        *,
        provider: str,
        model: str,
        quota_scope_id: str,
        lease_id: str,
        reserved_input_tokens: int,
        actual_prompt_tokens: Optional[int],
        allow_refund: bool,
        policy: QuotaPolicy,
        call_succeeded: bool = False,
        phase: str = "UNKNOWN",
        retry_number: int = 0,
        chunk_id: Optional[str] = None,
    ) -> None:
        await self._release_local_slot(
            provider, model, quota_scope_id, success=call_succeeded
        )
        released_at = time.time()
        self._log_quota(
            "RELEASE",
            provider=provider,
            model=model,
            phase=phase,
            retry_number=retry_number,
            chunk_id=chunk_id,
            lease_id=lease_id,
            inflight=self._active_count(provider, model, quota_scope_id),
            inflight_cap=self._inflight_cap(provider, model, quota_scope_id, policy),
            waiting=self._waiting_count(provider, model, quota_scope_id),
            released_at=released_at,
        )
        if not self.enabled or lease_id.startswith("local-"):
            return
        store = await self._ensure_store()
        prefix = self._prefix(provider, quota_scope_id, model, policy)
        release_kwargs = dict(
            prefix=prefix,
            lease_id=lease_id,
            reserved_input_tokens=reserved_input_tokens,
            actual_prompt_tokens=actual_prompt_tokens,
            tpm_limit=policy.tpm,
            allow_refund=allow_refund,
            call_succeeded=call_succeeded,
        )
        try:
            await store.release(**release_kwargs)
        except TypeError:
            release_kwargs.pop("call_succeeded", None)
            await store.release(**release_kwargs)
            if call_succeeded and hasattr(store, "set_degraded"):
                await store.set_degraded(prefix=prefix, degraded=False)

    async def apply_cooldown(
        self,
        *,
        provider: str,
        model: str,
        quota_scope_id: str,
        wait_seconds: float,
        policy: Optional[QuotaPolicy] = None,
    ) -> int:
        if wait_seconds <= 0:
            return 0
        state = self._pace(provider, model, quota_scope_id)
        async with state.cond:
            state.cooldown_until = max(
                state.cooldown_until, time.monotonic() + wait_seconds
            )
            state.degraded = True
            state.cond.notify_all()
        self.metrics.record_cooldown()
        if not self.enabled:
            return int(wait_seconds * 1000)
        store = await self._ensure_store()
        policy = policy or self.resolve_policy(provider, model, quota_scope_id)
        prefix = self._prefix(provider, quota_scope_id, model, policy)
        if hasattr(store, "_r"):
            t = await store._r.time()
            now_ms = int(t[0]) * 1000 + int(t[1]) // 1000
        else:
            now_ms = int(time.time() * 1000)
        until = now_ms + int(wait_seconds * 1000)
        result = await store.set_cooldown_until(prefix=prefix, until_ms=until)
        if hasattr(store, "set_degraded"):
            await store.set_degraded(prefix=prefix, degraded=True)
        return result

    async def cooldown_remaining_seconds(
        self, *, provider: str, model: str, quota_scope_id: str
    ) -> float:
        local = max(
            0.0,
            self._pace(provider, model, quota_scope_id).cooldown_until
            - time.monotonic(),
        )
        if not self.enabled:
            return local
        store = await self._ensure_store()
        try:
            policy = self.resolve_policy(provider, model, quota_scope_id)
        except QuotaPolicyMissingError:
            policy = None
        prefix = redis_prefix(
            provider,
            quota_scope_id,
            model,
            quota_group=policy.quota_group if policy else None,
        )
        remote = (await store.get_cooldown_remaining_ms(prefix=prefix)) / 1000.0
        return max(local, remote)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
