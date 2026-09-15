"""FASE 2: single retry path."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from openai import RateLimitError

from core.brevio.services.provider_quota.executor import ProviderCallExecutor
from core.brevio.services.provider_quota.observability import extract_rate_limit_signals
from core.brevio.services.provider_quota.policy import (
    DEFAULT_RETRY_ONLY_POLICY,
    QuotaPolicy,
)
from core.brevio.services.provider_quota.retry import RetryCoordinator


def _429():
    req = httpx.Request("POST", "https://example.com")
    resp = httpx.Response(
        429,
        request=req,
        headers={"retry-after": "0"},
        json={"error": {"message": "rate"}},
    )
    return RateLimitError("429", response=resp, body={"error": {"message": "rate"}})


def test_retry_after_beats_backoff():
    coord = RetryCoordinator()
    policy = DEFAULT_RETRY_ONLY_POLICY
    signals = extract_rate_limit_signals(_429())
    # force wait from header
    signals.wait_seconds = 7.0
    wait = coord.compute_wait_seconds(signals=signals, attempt=0, policy=policy)
    assert wait == 7.0


def test_should_not_retry_auth():
    from openai import AuthenticationError

    req = httpx.Request("POST", "https://example.com")
    resp = httpx.Response(401, request=req, json={"error": {"message": "no"}})
    err = AuthenticationError("no", response=resp, body=None)
    coord = RetryCoordinator()
    assert coord.should_retry(err, 0, DEFAULT_RETRY_ONLY_POLICY) is False


def test_daily_quota_exhausted_is_not_retried():
    from core.brevio.services.provider_quota.observability import RateLimitSignals

    coord = RetryCoordinator()
    signals = RateLimitSignals(
        status_code=429,
        wait_seconds=59.0,
        quota_id="GenerateRequestsPerDayPerProjectPerModel-FreeTier",
        quota_metric="generativelanguage.googleapis.com/generate_content_free_tier_requests",
        reason="You exceeded your current quota",
    )
    assert coord.is_daily_quota_exhausted(signals) is True
    decision = coord.decide(
        exc=_429(),
        attempt=0,
        policy=DEFAULT_RETRY_ONLY_POLICY,
        signals=signals,
    )
    assert decision.should_retry is False
    assert decision.reason == "daily_quota_exhausted"


@pytest.mark.asyncio
async def test_executor_retries_then_succeeds(monkeypatch):
    monkeypatch.setenv("PROVIDER_QUOTA_ENABLED", "false")
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise _429()
        return MagicMock(
            usage=MagicMock(prompt_tokens=10, completion_tokens=1, total_tokens=11)
        )

    policy = QuotaPolicy(
        provider="google",
        model="m",
        max_in_flight=10,
        lease_ttl_ms=1000,
        acquire_timeout_ms=1000,
        max_attempts=5,
        backoff_base_seconds=0.001,
        backoff_max_seconds=0.01,
        jitter_ratio=0.0,
        cooldown_on_429_seconds=0.001,
    )
    ex = ProviderCallExecutor()
    # bypass resolve
    result = await ex.execute(
        flaky,
        provider="google",
        model="m",
        quota_scope_id="platform",
        phase="MAP",
        estimated_input_tokens=10,
        policy=policy,
    )
    assert result is not None
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_api_service_max_retries_zero(monkeypatch):
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key="x", base_url="http://localhost", max_retries=0)
    assert client.max_retries == 0


def test_summary_service_has_no_tenacity_retry_attr():
    from unittest.mock import MagicMock

    import core.brevio.services.summary_service as ss_mod

    # Avoid DB on init
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        "core.brevio_api.core.database.AsyncDB.database", lambda self: MagicMock()
    )
    try:
        svc = ss_mod.SummaryService()
        assert not hasattr(svc.generate_summary_chunk, "retry")
        assert not hasattr(svc._execute_reduce_call, "retry")
        assert not hasattr(svc._execute_formatting_call, "retry")
    finally:
        monkeypatch.undo()


def test_body_retry_delay_beats_exponential_backoff():
    coord = RetryCoordinator()
    req = httpx.Request("POST", "https://example.com")
    resp = httpx.Response(429, request=req)
    err = RateLimitError(
        "429",
        response=resp,
        body=[
            {
                "error": {
                    "message": "Please retry in 12s.",
                    "details": [{"retryDelay": "12s"}],
                }
            }
        ],
    )
    signals = extract_rate_limit_signals(err)
    wait = coord.compute_wait_seconds(
        signals=signals, attempt=4, policy=DEFAULT_RETRY_ONLY_POLICY
    )
    assert wait >= 12.0
    decision = coord.decide(
        exc=err, attempt=0, policy=DEFAULT_RETRY_ONLY_POLICY, signals=signals
    )
    assert decision.should_retry is True
    assert decision.reason == "retry_after"


@pytest.mark.asyncio
async def test_local_cooldown_blocks_next_acquire(monkeypatch):
    import time

    monkeypatch.setenv("PROVIDER_QUOTA_ENABLED", "false")

    from core.brevio.services.provider_quota.manager import ProviderQuotaManager

    mgr = ProviderQuotaManager()
    policy = DEFAULT_RETRY_ONLY_POLICY
    await mgr.apply_cooldown(
        provider="any-provider",
        model="any-model",
        quota_scope_id="platform",
        wait_seconds=0.25,
    )
    t0 = time.monotonic()
    lease_id, _, _ = await mgr.acquire(
        provider="any-provider",
        model="any-model",
        quota_scope_id="platform",
        estimated_input_tokens=1,
        policy=policy,
    )
    assert time.monotonic() - t0 >= 0.2
    await mgr.release(
        provider="any-provider",
        model="any-model",
        quota_scope_id="platform",
        lease_id=lease_id,
        reserved_input_tokens=1,
        actual_prompt_tokens=1,
        allow_refund=True,
        policy=policy,
        call_succeeded=True,
    )


@pytest.mark.asyncio
async def test_degraded_mode_serializes_inflight_after_429(monkeypatch):
    monkeypatch.setenv("PROVIDER_QUOTA_ENABLED", "false")
    from core.brevio.services.provider_quota.manager import ProviderQuotaManager

    mgr = ProviderQuotaManager()
    policy = DEFAULT_RETRY_ONLY_POLICY
    kwargs = dict(
        provider="deepseek",
        model="deepseek-flash",
        quota_scope_id="platform",
        estimated_input_tokens=1,
        policy=policy,
    )
    await mgr.apply_cooldown(
        provider="deepseek",
        model="deepseek-flash",
        quota_scope_id="platform",
        wait_seconds=0.01,
    )
    await asyncio.sleep(0.02)

    second_started = asyncio.Event()

    async def hold():
        lease, _, _ = await mgr.acquire(**kwargs)
        await asyncio.sleep(0.15)
        await mgr.release(
            provider="deepseek",
            model="deepseek-flash",
            quota_scope_id="platform",
            lease_id=lease,
            reserved_input_tokens=1,
            actual_prompt_tokens=1,
            allow_refund=True,
            policy=policy,
            call_succeeded=True,
        )

    async def waiter():
        lease, _, _ = await mgr.acquire(**kwargs)
        second_started.set()
        await mgr.release(
            provider="deepseek",
            model="deepseek-flash",
            quota_scope_id="platform",
            lease_id=lease,
            reserved_input_tokens=1,
            actual_prompt_tokens=1,
            allow_refund=True,
            policy=policy,
            call_succeeded=True,
        )

    first = asyncio.create_task(hold())
    await asyncio.sleep(0.03)
    second = asyncio.create_task(waiter())
    await asyncio.sleep(0.08)
    assert not second_started.is_set()
    await first
    await asyncio.wait_for(second_started.wait(), timeout=1.0)
    await second
