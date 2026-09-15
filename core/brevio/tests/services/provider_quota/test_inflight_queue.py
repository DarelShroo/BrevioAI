"""max_in_flight must behave as a work queue — waiters acquire when slots free.

Mocks only: InMemoryQuotaStore + fake call() — no real Ollama/OpenAI/Gemini.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from core.brevio.services.provider_quota.errors import QuotaAcquireTimeoutError
from core.brevio.services.provider_quota.executor import ProviderCallExecutor
from core.brevio.services.provider_quota.manager import ProviderQuotaManager
from core.brevio.services.provider_quota.memory_store import InMemoryQuotaStore
from core.brevio.services.provider_quota.metrics import ProviderCallMetrics
from core.brevio.services.provider_quota.policy import QuotaPolicy, QuotaPolicyRegistry


def _policy(**overrides) -> QuotaPolicy:
    base = dict(
        provider="ollama",
        model="qwen3:14b",
        max_in_flight=1,
        lease_ttl_ms=60_000,
        # Short on purpose: capacity waits must NOT fail because of this.
        acquire_timeout_ms=200,
        max_attempts=3,
        backoff_base_seconds=0.01,
        backoff_max_seconds=0.05,
        jitter_ratio=0.0,
        rpm=None,
        tpm=None,
        cooldown_on_429_seconds=0.05,
        rate_limit_safety_margin=0.0,
        job_max_provider_requests=100,
        degraded_max_in_flight=1,
    )
    base.update(overrides)
    return QuotaPolicy(**base)


def _ok():
    return MagicMock(
        usage=MagicMock(prompt_tokens=4, completion_tokens=1, total_tokens=5)
    )


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setenv("PROVIDER_QUOTA_ENABLED", "true")


@pytest.fixture
def queue_backend(enabled):
    store = InMemoryQuotaStore()
    policy = _policy()
    registry = QuotaPolicyRegistry([policy])
    metrics = ProviderCallMetrics()
    mgr = ProviderQuotaManager(store=store, registry=registry, metrics=metrics)
    ex = ProviderCallExecutor(quota_manager=mgr, metrics=metrics)
    return store, mgr, ex, policy


async def _run_chunk(
    ex: ProviderCallExecutor,
    policy: QuotaPolicy,
    *,
    phase: str,
    chunk_id: str,
    hold_s: float,
    live: dict,
    fail: bool = False,
):
    async def call():
        live["n"] += 1
        live["peak"] = max(live["peak"], live["n"])
        try:
            await asyncio.sleep(hold_s)
            if fail:
                raise RuntimeError(f"provider boom {chunk_id}")
            return _ok()
        finally:
            live["n"] -= 1

    return await ex.execute(
        call,
        provider=policy.provider,
        model=policy.model,
        quota_scope_id="platform",
        phase=phase,
        estimated_input_tokens=1,
        chunk_id=chunk_id,
        policy=policy,
    )


@pytest.mark.asyncio
async def test_max_in_flight_1_five_chunks_queue_no_timeout(queue_backend):
    """1. max_in_flight=1, 5 concurrent → max active=1, all complete, no timeout."""
    _store, _mgr, ex, policy = queue_backend
    live = {"n": 0, "peak": 0}
    results = await asyncio.gather(
        *[
            _run_chunk(ex, policy, phase="MAP", chunk_id=str(i), hold_s=0.05, live=live)
            for i in range(5)
        ]
    )
    assert len(results) == 5
    assert live["peak"] == 1
    assert live["n"] == 0


@pytest.mark.asyncio
async def test_max_in_flight_2_five_chunks_cap(queue_backend):
    """2. max_in_flight=2, 5 chunks → max active=2, all complete."""
    store, _mgr, _ex, _ = queue_backend
    policy = _policy(max_in_flight=2, acquire_timeout_ms=200)
    registry = QuotaPolicyRegistry([policy])
    mgr = ProviderQuotaManager(
        store=store, registry=registry, metrics=ProviderCallMetrics()
    )
    ex = ProviderCallExecutor(quota_manager=mgr, metrics=mgr.metrics)
    live = {"n": 0, "peak": 0}
    await asyncio.gather(
        *[
            _run_chunk(ex, policy, phase="MAP", chunk_id=str(i), hold_s=0.05, live=live)
            for i in range(5)
        ]
    )
    assert live["peak"] == 2
    assert live["n"] == 0


@pytest.mark.asyncio
async def test_slow_first_others_wait_then_acquire(queue_backend):
    """3. First request slow; others wait then acquire; no fail for waiting."""
    _store, _mgr, ex, policy = queue_backend
    # acquire_timeout_ms=200 would fail if capacity waits used the deadline.
    policy = _policy(max_in_flight=1, acquire_timeout_ms=150)
    live = {"n": 0, "peak": 0}
    started = []

    async def tracked(i: int, hold: float):
        started.append(i)
        return await _run_chunk(
            ex, policy, phase="MAP", chunk_id=str(i), hold_s=hold, live=live
        )

    await asyncio.gather(
        tracked(0, 0.35),
        tracked(1, 0.05),
        tracked(2, 0.05),
    )
    assert live["peak"] == 1
    assert set(started) == {0, 1, 2}


@pytest.mark.asyncio
async def test_provider_exception_releases_slot_for_waiter(queue_backend):
    """4. Provider exception → slot released; next waiter acquires."""
    _store, mgr, ex, policy = queue_backend
    live = {"n": 0, "peak": 0}

    with pytest.raises(RuntimeError, match="provider boom"):
        await _run_chunk(
            ex, policy, phase="MAP", chunk_id="0", hold_s=0.05, live=live, fail=True
        )
    assert mgr._active_count(policy.provider, policy.model, "platform") == 0

    await _run_chunk(ex, policy, phase="MAP", chunk_id="1", hold_s=0.05, live=live)
    assert live["peak"] == 1
    assert live["n"] == 0


@pytest.mark.asyncio
async def test_cross_manager_capacity_queue_no_timeout(queue_backend):
    """Two managers sharing Redis/memory store: max_in_flight wait does not timeout."""
    store, mgr_a, _ex, _ = queue_backend
    policy = _policy(max_in_flight=1, acquire_timeout_ms=120)
    registry = QuotaPolicyRegistry([policy])
    mgr_b = ProviderQuotaManager(
        store=store, registry=registry, metrics=ProviderCallMetrics()
    )
    lease_a, _, _ = await mgr_a.acquire(
        provider=policy.provider,
        model=policy.model,
        quota_scope_id="platform",
        estimated_input_tokens=1,
        policy=policy,
        phase="MAP",
        chunk_id="a",
    )
    waiter = asyncio.create_task(
        mgr_b.acquire(
            provider=policy.provider,
            model=policy.model,
            quota_scope_id="platform",
            estimated_input_tokens=1,
            policy=policy,
            phase="REDUCE",
            chunk_id="b",
        )
    )
    await asyncio.sleep(0.25)
    assert not waiter.done(), "capacity waiter must not fail while holder is active"

    await mgr_a.release(
        provider=policy.provider,
        model=policy.model,
        quota_scope_id="platform",
        lease_id=lease_a,
        reserved_input_tokens=1,
        actual_prompt_tokens=1,
        allow_refund=True,
        policy=policy,
        call_succeeded=True,
        phase="MAP",
        chunk_id="a",
    )
    lease_b, _, _ = await asyncio.wait_for(waiter, timeout=1.0)
    await mgr_b.release(
        provider=policy.provider,
        model=policy.model,
        quota_scope_id="platform",
        lease_id=lease_b,
        reserved_input_tokens=1,
        actual_prompt_tokens=1,
        allow_refund=True,
        policy=policy,
        call_succeeded=True,
        phase="REDUCE",
        chunk_id="b",
    )


@pytest.mark.asyncio
async def test_cancel_holder_releases_lease(queue_backend):
    """5. Cancel coroutine holding lease → lease released for next waiter."""
    _store, mgr, ex, policy = queue_backend
    live = {"n": 0, "peak": 0}
    holder_entered = asyncio.Event()

    async def hold_forever():
        async def call():
            live["n"] += 1
            live["peak"] = max(live["peak"], live["n"])
            holder_entered.set()
            try:
                await asyncio.sleep(3600)
            finally:
                live["n"] -= 1
            return _ok()

        return await ex.execute(
            call,
            provider=policy.provider,
            model=policy.model,
            quota_scope_id="platform",
            phase="MAP",
            estimated_input_tokens=1,
            chunk_id="hold",
            policy=policy,
        )

    task = asyncio.create_task(hold_forever())
    await asyncio.wait_for(holder_entered.wait(), timeout=1.0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    # Next acquire must succeed quickly — lease was released.
    lease, _, _ = await asyncio.wait_for(
        mgr.acquire(
            provider=policy.provider,
            model=policy.model,
            quota_scope_id="platform",
            estimated_input_tokens=1,
            policy=policy,
            phase="MAP",
            chunk_id="next",
        ),
        timeout=1.0,
    )
    await mgr.release(
        provider=policy.provider,
        model=policy.model,
        quota_scope_id="platform",
        lease_id=lease,
        reserved_input_tokens=1,
        actual_prompt_tokens=1,
        allow_refund=True,
        policy=policy,
        call_succeeded=True,
        phase="MAP",
        chunk_id="next",
    )
    assert mgr._active_count(policy.provider, policy.model, "platform") == 0


@pytest.mark.asyncio
async def test_reduce_failure_releases_slot(queue_backend):
    """6. REDUCE failure → slot released."""
    _store, mgr, ex, policy = queue_backend
    live = {"n": 0, "peak": 0}
    with pytest.raises(RuntimeError, match="provider boom"):
        await _run_chunk(
            ex, policy, phase="REDUCE", chunk_id="R", hold_s=0.02, live=live, fail=True
        )
    assert mgr._active_count(policy.provider, policy.model, "platform") == 0

    # MAP and REDUCE share the same mechanism — next MAP acquires.
    await _run_chunk(ex, policy, phase="MAP", chunk_id="after", hold_s=0.02, live=live)
    assert live["peak"] == 1


@pytest.mark.asyncio
async def test_no_deadlock_mixed_map_reduce(queue_backend):
    """7. Mixed MAP/REDUCE under cap=1 completes without deadlock/timeout."""
    _store, _mgr, ex, policy = queue_backend
    policy = _policy(max_in_flight=1, acquire_timeout_ms=100)
    live = {"n": 0, "peak": 0}
    phases = ["MAP", "MAP", "REDUCE", "MAP", "REDUCE"]
    await asyncio.wait_for(
        asyncio.gather(
            *[
                _run_chunk(
                    ex, policy, phase=phases[i], chunk_id=str(i), hold_s=0.04, live=live
                )
                for i in range(5)
            ]
        ),
        timeout=5.0,
    )
    assert live["peak"] == 1
    assert live["n"] == 0


@pytest.mark.asyncio
async def test_capacity_wait_does_not_raise_acquire_timeout(queue_backend):
    """Waiting for max_in_flight must not raise QuotaAcquireTimeoutError."""
    _store, mgr, _ex, policy = queue_backend
    policy = _policy(max_in_flight=1, acquire_timeout_ms=100)
    lease, _, _ = await mgr.acquire(
        provider=policy.provider,
        model=policy.model,
        quota_scope_id="platform",
        estimated_input_tokens=1,
        policy=policy,
        phase="MAP",
    )

    waiter = asyncio.create_task(
        mgr.acquire(
            provider=policy.provider,
            model=policy.model,
            quota_scope_id="platform",
            estimated_input_tokens=1,
            policy=policy,
            phase="REDUCE",
            chunk_id="waiter",
        )
    )
    await asyncio.sleep(0.25)  # longer than acquire_timeout_ms
    assert not waiter.done()

    await mgr.release(
        provider=policy.provider,
        model=policy.model,
        quota_scope_id="platform",
        lease_id=lease,
        reserved_input_tokens=1,
        actual_prompt_tokens=1,
        allow_refund=True,
        policy=policy,
        call_succeeded=True,
        phase="MAP",
    )
    w_lease, _, _ = await asyncio.wait_for(waiter, timeout=1.0)
    await mgr.release(
        provider=policy.provider,
        model=policy.model,
        quota_scope_id="platform",
        lease_id=w_lease,
        reserved_input_tokens=1,
        actual_prompt_tokens=1,
        allow_refund=True,
        policy=policy,
        call_succeeded=True,
        phase="REDUCE",
        chunk_id="waiter",
    )


@pytest.mark.asyncio
async def test_rpm_denial_still_times_out(queue_backend):
    """Non-capacity denials still honor acquire_timeout_ms."""
    store, _mgr, _ex, _ = queue_backend
    policy = _policy(max_in_flight=10, rpm=1, acquire_timeout_ms=150)
    registry = QuotaPolicyRegistry([policy])
    mgr = ProviderQuotaManager(
        store=store, registry=registry, metrics=ProviderCallMetrics()
    )
    lease, _, _ = await mgr.acquire(
        provider=policy.provider,
        model=policy.model,
        quota_scope_id="platform",
        estimated_input_tokens=1,
        policy=policy,
    )
    with pytest.raises(QuotaAcquireTimeoutError) as ei:
        await mgr.acquire(
            provider=policy.provider,
            model=policy.model,
            quota_scope_id="platform",
            estimated_input_tokens=1,
            policy=policy,
        )
    assert ei.value.last_reason == "rpm"
    await mgr.release(
        provider=policy.provider,
        model=policy.model,
        quota_scope_id="platform",
        lease_id=lease,
        reserved_input_tokens=1,
        actual_prompt_tokens=1,
        allow_refund=True,
        policy=policy,
        call_succeeded=True,
    )


@pytest.mark.asyncio
async def test_inference_error_is_not_acquire_timeout(queue_backend):
    """Acquire timeout ≠ inference/provider errors (distinct exception types)."""
    _store, _mgr, ex, policy = queue_backend
    live = {"n": 0, "peak": 0}
    with pytest.raises(RuntimeError, match="provider boom") as ei:
        await _run_chunk(
            ex, policy, phase="MAP", chunk_id="inf", hold_s=0.01, live=live, fail=True
        )
    assert not isinstance(ei.value, QuotaAcquireTimeoutError)


@pytest.mark.asyncio
async def test_reduce_runs_after_map_when_slot_free(queue_backend):
    """REDUCE must acquire after MAP releases the sole inflight slot."""
    _store, _mgr, ex, policy = queue_backend
    live = {"n": 0, "peak": 0}
    order: list[str] = []

    async def map_then():
        order.append("map_start")
        await _run_chunk(ex, policy, phase="MAP", chunk_id="m", hold_s=0.08, live=live)
        order.append("map_done")

    async def reduce_after():
        await asyncio.sleep(0.01)
        order.append("reduce_start")
        await _run_chunk(
            ex, policy, phase="REDUCE", chunk_id="r", hold_s=0.04, live=live
        )
        order.append("reduce_done")

    await asyncio.gather(map_then(), reduce_after())
    assert live["peak"] == 1
    assert order.index("map_done") < order.index("reduce_done")


@pytest.mark.asyncio
async def test_multi_waiter_no_acquire_polling_storm(queue_backend):
    """Many pending docs/chunks must not multiply Redis acquire polls (local gate)."""
    store, mgr, ex, policy = queue_backend
    live = {"n": 0, "peak": 0}
    acquire_calls = {"n": 0}
    real_acquire = store.acquire

    async def counting_acquire(**kwargs):
        acquire_calls["n"] += 1
        return await real_acquire(**kwargs)

    store.acquire = counting_acquire  # type: ignore[method-assign]

    holder_entered = asyncio.Event()

    async def holder():
        async def call():
            live["n"] += 1
            live["peak"] = max(live["peak"], live["n"])
            holder_entered.set()
            try:
                await asyncio.sleep(0.35)
                return _ok()
            finally:
                live["n"] -= 1

        return await ex.execute(
            call,
            provider=policy.provider,
            model=policy.model,
            quota_scope_id="platform",
            phase="MAP",
            estimated_input_tokens=1,
            chunk_id="holder",
            policy=policy,
        )

    async def waiter(i: int):
        await holder_entered.wait()
        return await _run_chunk(
            ex, policy, phase="MAP", chunk_id=f"w{i}", hold_s=0.02, live=live
        )

    # Snapshot polls after holder has the lease and 8 waiters are pending.
    task_h = asyncio.create_task(holder())
    await asyncio.wait_for(holder_entered.wait(), timeout=1.0)
    waiters = [asyncio.create_task(waiter(i)) for i in range(8)]
    await asyncio.sleep(0.2)
    polls_while_busy = acquire_calls["n"]
    await asyncio.gather(task_h, *waiters)

    # Local max_in_flight gate: only the active holder (plus at most one
    # Redis-loop contender after release) polls — not 8× high-frequency storms.
    # Allow some retries/jitter but keep well below waiter_count * (0.2/0.05).
    assert live["peak"] == 1
    assert (
        polls_while_busy < 40
    ), f"polling storm: {polls_while_busy} acquires while busy"
    assert mgr._active_count(policy.provider, policy.model, "platform") == 0
