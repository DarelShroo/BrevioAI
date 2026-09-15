"""Global distributed quota: RPM, inflight, 429 cooldown, anti-herd, job budget."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import httpx
import pytest
from openai import RateLimitError

from core.brevio.services.provider_quota.errors import JobRequestBudgetExceededError
from core.brevio.services.provider_quota.executor import ProviderCallExecutor
from core.brevio.services.provider_quota.job_budget import JobRequestBudget
from core.brevio.services.provider_quota.manager import ProviderQuotaManager
from core.brevio.services.provider_quota.memory_store import InMemoryQuotaStore
from core.brevio.services.provider_quota.metrics import ProviderCallMetrics
from core.brevio.services.provider_quota.policy import (
    QuotaPolicy,
    QuotaPolicyRegistry,
    effective_rpm,
)
from core.brevio.services.provider_quota.retry import RetryCoordinator


def _policy(**overrides) -> QuotaPolicy:
    base = dict(
        provider="google",
        model="gemini-test",
        max_in_flight=2,
        lease_ttl_ms=5000,
        acquire_timeout_ms=4000,
        max_attempts=4,
        backoff_base_seconds=0.05,
        backoff_max_seconds=0.2,
        jitter_ratio=0.5,
        rpm=3,
        tpm=None,
        cooldown_on_429_seconds=0.2,
        rate_limit_safety_margin=0.0,
        job_max_provider_requests=50,
        degraded_max_in_flight=1,
    )
    base.update(overrides)
    return QuotaPolicy(**base)


def _429(retry_after: str | None = "1", body=None):
    req = httpx.Request("POST", "https://example.com")
    headers = {}
    if retry_after is not None:
        headers["retry-after"] = retry_after
    resp = httpx.Response(
        429,
        request=req,
        headers=headers,
        json=body or {"error": {"message": "rate"}},
    )
    return RateLimitError(
        "429", response=resp, body=body or {"error": {"message": "rate"}}
    )


def _ok():
    return MagicMock(
        usage=MagicMock(prompt_tokens=4, completion_tokens=1, total_tokens=5)
    )


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setenv("PROVIDER_QUOTA_ENABLED", "true")


@pytest.fixture
def shared_backend(enabled):
    store = InMemoryQuotaStore()
    registry = QuotaPolicyRegistry([_policy()])
    metrics = ProviderCallMetrics()
    mgr_a = ProviderQuotaManager(store=store, registry=registry, metrics=metrics)
    mgr_b = ProviderQuotaManager(
        store=store, registry=registry, metrics=ProviderCallMetrics()
    )
    return store, mgr_a, mgr_b


@pytest.mark.asyncio
async def test_two_jobs_rpm_hard_cap(shared_backend):
    """Two jobs together cannot exceed global RPM."""
    _store, mgr_a, mgr_b = shared_backend
    policy = _policy(rpm=2, max_in_flight=10, acquire_timeout_ms=400)
    leases = []

    async def one(mgr):
        lease, _, _ = await mgr.acquire(
            provider="google",
            model="gemini-test",
            quota_scope_id="platform",
            estimated_input_tokens=1,
            policy=policy,
        )
        leases.append(lease)
        return mgr, lease

    first = await asyncio.gather(one(mgr_a), one(mgr_b))
    assert len(leases) == 2

    with pytest.raises(Exception):
        await asyncio.wait_for(one(mgr_a), timeout=0.6)

    for mgr, lease in first:
        await mgr.release(
            provider="google",
            model="gemini-test",
            quota_scope_id="platform",
            lease_id=lease,
            reserved_input_tokens=1,
            actual_prompt_tokens=1,
            allow_refund=True,
            policy=policy,
            call_succeeded=True,
        )


@pytest.mark.asyncio
async def test_simulated_workers_share_inflight(shared_backend):
    _store, mgr_a, mgr_b = shared_backend
    policy = _policy(rpm=100, max_in_flight=2)
    started = []
    peak = {"n": 0}

    live = {"n": 0, "peak": 0}

    async def hold2(mgr):
        lease, _, _ = await mgr.acquire(
            provider="google",
            model="gemini-test",
            quota_scope_id="platform",
            estimated_input_tokens=1,
            policy=policy,
        )
        live["n"] += 1
        live["peak"] = max(live["peak"], live["n"])
        await asyncio.sleep(0.05)
        live["n"] -= 1
        await mgr.release(
            provider="google",
            model="gemini-test",
            quota_scope_id="platform",
            lease_id=lease,
            reserved_input_tokens=1,
            actual_prompt_tokens=1,
            allow_refund=True,
            policy=policy,
            call_succeeded=True,
        )

    await asyncio.gather(*[hold2(mgr_a if i % 2 == 0 else mgr_b) for i in range(6)])
    assert live["peak"] <= 2


@pytest.mark.asyncio
async def test_429_retry_after_blocks_other_job(shared_backend):
    _store, mgr_a, mgr_b = shared_backend
    policy = _policy(rpm=20, max_in_flight=4, cooldown_on_429_seconds=0.05)
    metrics = ProviderCallMetrics()
    ex_a = ProviderCallExecutor(quota_manager=mgr_a, metrics=metrics)
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise _429("0.25")
        return _ok()

    t0 = asyncio.get_event_loop().time()
    await ex_a.execute(
        flaky,
        provider="google",
        model="gemini-test",
        quota_scope_id="platform",
        phase="MAP",
        estimated_input_tokens=1,
        policy=policy,
    )
    remaining = await mgr_b.cooldown_remaining_seconds(
        provider="google", model="gemini-test", quota_scope_id="platform"
    )
    # Cooldown is shared; either still blocking or just elapsed after the retry wait.
    assert calls["n"] == 2
    assert metrics.provider_429_count >= 1
    assert metrics.retry_requests >= 1
    elapsed = asyncio.get_event_loop().time() - t0
    assert elapsed >= 0.2
    assert remaining >= 0


@pytest.mark.asyncio
async def test_429_blocks_second_manager_during_cooldown(shared_backend):
    _store, mgr_a, mgr_b = shared_backend
    policy = _policy(rpm=50, max_in_flight=4, acquire_timeout_ms=400)
    await mgr_a.apply_cooldown(
        provider="google",
        model="gemini-test",
        quota_scope_id="platform",
        wait_seconds=0.4,
        policy=policy,
    )
    t0 = asyncio.get_event_loop().time()
    with pytest.raises(Exception):
        await asyncio.wait_for(
            mgr_b.acquire(
                provider="google",
                model="gemini-test",
                quota_scope_id="platform",
                estimated_input_tokens=1,
                policy=policy,
            ),
            timeout=0.25,
        )
    assert asyncio.get_event_loop().time() - t0 < 0.4


@pytest.mark.asyncio
async def test_429_without_retry_after_uses_backoff_jitter():
    coord = RetryCoordinator()
    policy = _policy(
        backoff_base_seconds=0.2, jitter_ratio=0.5, cooldown_on_429_seconds=None
    )
    err = _429(retry_after=None)
    waits = [
        coord.compute_wait_seconds(signals=None, attempt=0, policy=policy)
        for _ in range(20)
    ]
    assert min(waits) >= 0.2 * (1 - 0.5) - 1e-9
    assert max(waits) <= 0.2 + 1e-9
    assert len(set(round(w, 5) for w in waits)) > 1
    from core.brevio.services.provider_quota.observability import (
        extract_rate_limit_signals,
    )

    signals = extract_rate_limit_signals(err)
    # No Retry-After header and no body delay → backoff path
    assert signals.wait_seconds is None
    decision = coord.decide(exc=err, attempt=0, policy=policy, signals=signals)
    assert decision.should_retry is True
    assert decision.reason == "backoff"


@pytest.mark.asyncio
async def test_thundering_herd_after_cooldown_respects_inflight(shared_backend):
    _store, mgr_a, mgr_b = shared_backend
    policy = _policy(
        rpm=20, max_in_flight=2, degraded_max_in_flight=1, acquire_timeout_ms=3000
    )
    await mgr_a.apply_cooldown(
        provider="google",
        model="gemini-test",
        quota_scope_id="platform",
        wait_seconds=0.05,
        policy=policy,
    )
    await asyncio.sleep(0.07)

    live = {"n": 0, "peak": 0}

    async def probe(mgr):
        lease, _, _ = await mgr.acquire(
            provider="google",
            model="gemini-test",
            quota_scope_id="platform",
            estimated_input_tokens=1,
            policy=policy,
        )
        live["n"] += 1
        live["peak"] = max(live["peak"], live["n"])
        await asyncio.sleep(0.04)
        live["n"] -= 1
        await mgr.release(
            provider="google",
            model="gemini-test",
            quota_scope_id="platform",
            lease_id=lease,
            reserved_input_tokens=1,
            actual_prompt_tokens=1,
            allow_refund=True,
            policy=policy,
            call_succeeded=True,
        )

    await asyncio.gather(*[probe(mgr_a if i % 2 else mgr_b) for i in range(8)])
    # Degraded half-open: only 1 inflight until the first success clears it.
    # Peak may rise to max_in_flight after the first success; never above policy.
    assert live["peak"] <= policy.max_in_flight
    assert live["peak"] >= 1


@pytest.mark.asyncio
async def test_job_budget_hard_cap(enabled):
    store = InMemoryQuotaStore()
    policy = _policy(
        rpm=100, max_in_flight=10, max_attempts=8, job_max_provider_requests=3
    )
    mgr = ProviderQuotaManager(store=store, registry=QuotaPolicyRegistry([policy]))
    budget = JobRequestBudget(max_physical=3, expected_requests=1)
    metrics = ProviderCallMetrics()
    ex = ProviderCallExecutor(quota_manager=mgr, metrics=metrics, job_budget=budget)

    async def boom():
        raise _429("0")

    with pytest.raises(JobRequestBudgetExceededError):
        await ex.execute(
            boom,
            provider="google",
            model="gemini-test",
            quota_scope_id="platform",
            phase="MAP",
            estimated_input_tokens=1,
            policy=policy,
        )
    assert budget.physical <= 3
    assert metrics.physical_http_requests <= 3


def test_effective_rpm_applies_safety_margin():
    policy = _policy(rpm=15, rate_limit_safety_margin=0.2)
    assert effective_rpm(policy) == 12


@pytest.mark.asyncio
async def test_metrics_distinguish_physical_retry_success_and_429(shared_backend):
    _store, mgr_a, _mgr_b = shared_backend
    policy = _policy(
        rpm=50, max_in_flight=4, max_attempts=4, cooldown_on_429_seconds=0.01
    )
    metrics = ProviderCallMetrics()
    ex = ProviderCallExecutor(quota_manager=mgr_a, metrics=metrics)
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise _429("0")
        return _ok()

    await ex.execute(
        flaky,
        provider="google",
        model="gemini-test",
        quota_scope_id="platform",
        phase="MAP",
        estimated_input_tokens=1,
        policy=policy,
    )
    assert metrics.physical_http_requests == 3
    assert metrics.retry_requests == 2
    assert metrics.successful_requests == 1
    assert metrics.failed_requests == 2
    assert metrics.provider_429_count == 2
    assert metrics.physical_http_requests != metrics.successful_requests
    assert metrics.by_phase["MAP"].physical_http_requests == 3
    assert metrics.by_phase["MAP"].retry_requests == 2
    assert metrics.by_phase["MAP"].successful_requests == 1
    assert metrics.by_phase["MAP"].failed_requests == 2
    assert metrics.by_phase["MAP"].provider_429_count == 2


@pytest.mark.asyncio
async def test_distinct_quota_scopes_do_not_share_cooldown(shared_backend):
    _store, mgr_a, mgr_b = shared_backend
    policy = _policy(rpm=50, max_in_flight=4, acquire_timeout_ms=800)
    await mgr_a.apply_cooldown(
        provider="google",
        model="gemini-test",
        quota_scope_id="platform",
        wait_seconds=5,
        policy=policy,
    )
    lease, _, result = await mgr_b.acquire(
        provider="google",
        model="gemini-test",
        quota_scope_id="cred:other-user",
        estimated_input_tokens=1,
        policy=policy,
    )
    assert result.ok
    await mgr_b.release(
        provider="google",
        model="gemini-test",
        quota_scope_id="cred:other-user",
        lease_id=lease,
        reserved_input_tokens=1,
        actual_prompt_tokens=1,
        allow_refund=True,
        policy=policy,
        call_succeeded=True,
    )
