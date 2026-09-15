"""Redis Lua: max_in_flight, leases, RPM, TPM, cooldown, fail-closed."""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
import redis.asyncio as redis_async

from core.brevio.services.provider_quota.errors import (
    ProviderQuotaUnavailableError,
    QuotaPolicyMissingError,
)
from core.brevio.services.provider_quota.keys import redis_prefix
from core.brevio.services.provider_quota.manager import ProviderQuotaManager
from core.brevio.services.provider_quota.policy import (
    QuotaPolicy,
    QuotaPolicyRegistry,
    load_quota_policies,
)
from core.brevio.services.provider_quota.redis_store import RedisQuotaStore

pytestmark = pytest.mark.redis

REDIS_URL = os.getenv("PROVIDER_QUOTA_TEST_REDIS_URL", "redis://127.0.0.1:6379/15")
FIXTURE_YAML = Path(__file__).parent / "fixtures" / "test_quotas.yaml"


def _policy(**overrides) -> QuotaPolicy:
    base = dict(
        provider="google",
        model="gemini-3.1-flash-lite",
        max_in_flight=3,
        lease_ttl_ms=1500,
        acquire_timeout_ms=5000,
        max_attempts=3,
        backoff_base_seconds=0.01,
        backoff_max_seconds=0.05,
        jitter_ratio=0.0,
        rpm=100,
        tpm=100000,
        cooldown_on_429_seconds=1,
    )
    base.update(overrides)
    return QuotaPolicy(**base)


@pytest_asyncio.fixture
async def store():
    client = redis_async.from_url(REDIS_URL, decode_responses=False)
    try:
        await client.ping()
    except Exception as e:
        await client.aclose()
        pytest.skip(f"Redis not available at {REDIS_URL}: {e}")
    await client.flushdb()
    s = RedisQuotaStore(client)
    yield s
    await client.flushdb()
    await client.aclose()


@pytest.mark.asyncio
async def test_acquire_respects_max_in_flight(store):
    prefix = redis_prefix("google", "platform", "m")
    ids = []
    for _ in range(3):
        r = await store.acquire(
            prefix=prefix,
            max_in_flight=3,
            lease_ttl_ms=5000,
            rpm_limit=None,
            tpm_limit=None,
            reserved_input_tokens=0,
        )
        assert r.ok
        ids.append(r.lease_id)
    denied = await store.acquire(
        prefix=prefix,
        max_in_flight=3,
        lease_ttl_ms=5000,
        rpm_limit=None,
        tpm_limit=None,
        reserved_input_tokens=0,
    )
    assert not denied.ok
    assert denied.reason == "max_in_flight"


@pytest.mark.asyncio
async def test_release_idempotent(store):
    prefix = redis_prefix("google", "platform", "m")
    r = await store.acquire(
        prefix=prefix,
        max_in_flight=1,
        lease_ttl_ms=5000,
        rpm_limit=None,
        tpm_limit=None,
        reserved_input_tokens=0,
    )
    await store.release(
        prefix=prefix,
        lease_id=r.lease_id,
        reserved_input_tokens=0,
        actual_prompt_tokens=None,
        tpm_limit=None,
        allow_refund=False,
    )
    await store.release(
        prefix=prefix,
        lease_id=r.lease_id,
        reserved_input_tokens=0,
        actual_prompt_tokens=None,
        tpm_limit=None,
        allow_refund=False,
    )
    again = await store.acquire(
        prefix=prefix,
        max_in_flight=1,
        lease_ttl_ms=5000,
        rpm_limit=None,
        tpm_limit=None,
        reserved_input_tokens=0,
    )
    assert again.ok


@pytest.mark.asyncio
async def test_lease_expires_and_reclaimed(store):
    prefix = redis_prefix("google", "platform", "lease-ttl")
    r = await store.acquire(
        prefix=prefix,
        max_in_flight=1,
        lease_ttl_ms=400,
        rpm_limit=None,
        tpm_limit=None,
        reserved_input_tokens=0,
    )
    assert r.ok
    # Without release, wait for TTL
    await asyncio.sleep(0.6)
    reclaim = await store.acquire(
        prefix=prefix,
        max_in_flight=1,
        lease_ttl_ms=2000,
        rpm_limit=None,
        tpm_limit=None,
        reserved_input_tokens=0,
    )
    assert reclaim.ok, reclaim.reason


@pytest.mark.asyncio
async def test_rpm_sliding_window(store):
    prefix = redis_prefix("google", "platform", "rpm")
    for i in range(5):
        r = await store.acquire(
            prefix=prefix,
            max_in_flight=100,
            lease_ttl_ms=5000,
            rpm_limit=5,
            tpm_limit=None,
            reserved_input_tokens=0,
            lease_id=str(uuid.uuid4()),
        )
        assert r.ok, f"i={i} {r.reason}"
        await store.release(
            prefix=prefix,
            lease_id=r.lease_id,
            reserved_input_tokens=0,
            actual_prompt_tokens=None,
            tpm_limit=None,
            allow_refund=False,
        )
    denied = await store.acquire(
        prefix=prefix,
        max_in_flight=100,
        lease_ttl_ms=5000,
        rpm_limit=5,
        tpm_limit=None,
        reserved_input_tokens=0,
    )
    assert not denied.ok
    assert denied.reason == "rpm"


@pytest.mark.asyncio
async def test_tpm_input_only_blocks(store):
    prefix = redis_prefix("google", "platform", "tpm")
    r = await store.acquire(
        prefix=prefix,
        max_in_flight=10,
        lease_ttl_ms=5000,
        rpm_limit=None,
        tpm_limit=1000,
        reserved_input_tokens=800,
    )
    assert r.ok
    denied = await store.acquire(
        prefix=prefix,
        max_in_flight=10,
        lease_ttl_ms=5000,
        rpm_limit=None,
        tpm_limit=1000,
        reserved_input_tokens=300,
    )
    assert not denied.ok
    assert denied.reason == "tpm"


@pytest.mark.asyncio
async def test_tpm_settle_refund_on_success(store):
    prefix = redis_prefix("google", "platform", "tpm-settle")
    r = await store.acquire(
        prefix=prefix,
        max_in_flight=10,
        lease_ttl_ms=5000,
        rpm_limit=None,
        tpm_limit=1000,
        reserved_input_tokens=800,
    )
    await store.release(
        prefix=prefix,
        lease_id=r.lease_id,
        reserved_input_tokens=800,
        actual_prompt_tokens=200,
        tpm_limit=1000,
        allow_refund=True,
    )
    # 800 reserved, 200 actual → refund 600 → ~800 left + refill; should allow 700
    ok = await store.acquire(
        prefix=prefix,
        max_in_flight=10,
        lease_ttl_ms=5000,
        rpm_limit=None,
        tpm_limit=1000,
        reserved_input_tokens=700,
    )
    assert ok.ok


@pytest.mark.asyncio
async def test_tpm_no_refund_when_may_have_reached_provider(store):
    prefix = redis_prefix("google", "platform", "tpm-norefund")
    r = await store.acquire(
        prefix=prefix,
        max_in_flight=10,
        lease_ttl_ms=5000,
        rpm_limit=None,
        tpm_limit=1000,
        reserved_input_tokens=900,
    )
    await store.release(
        prefix=prefix,
        lease_id=r.lease_id,
        reserved_input_tokens=900,
        actual_prompt_tokens=None,
        tpm_limit=1000,
        allow_refund=False,
    )
    denied = await store.acquire(
        prefix=prefix,
        max_in_flight=10,
        lease_ttl_ms=5000,
        rpm_limit=None,
        tpm_limit=1000,
        reserved_input_tokens=200,
    )
    assert not denied.ok
    assert denied.reason == "tpm"


@pytest.mark.asyncio
async def test_cooldown_max_not_multiplied(store):
    prefix = redis_prefix("google", "platform", "cd")
    t = await store._r.time()
    now_ms = int(t[0]) * 1000 + int(t[1]) // 1000
    u1 = await store.set_cooldown_until(prefix=prefix, until_ms=now_ms + 2000)
    u2 = await store.set_cooldown_until(prefix=prefix, until_ms=now_ms + 1000)
    assert u2 == u1  # MAX keeps larger
    denied = await store.acquire(
        prefix=prefix,
        max_in_flight=10,
        lease_ttl_ms=1000,
        rpm_limit=None,
        tpm_limit=None,
        reserved_input_tokens=0,
    )
    assert not denied.ok
    assert denied.reason == "cooldown"


@pytest.mark.asyncio
async def test_fail_closed_missing_policy(monkeypatch):
    monkeypatch.setenv("PROVIDER_QUOTA_ENABLED", "true")
    monkeypatch.delenv("PROVIDER_QUOTA_CONFIG_PATH", raising=False)
    mgr = ProviderQuotaManager(registry=QuotaPolicyRegistry([]), redis_url=REDIS_URL)
    with pytest.raises(QuotaPolicyMissingError):
        mgr.resolve_policy("google", "gemini-3.1-flash-lite", "platform")


@pytest.mark.asyncio
async def test_fail_closed_redis_down(monkeypatch):
    monkeypatch.setenv("PROVIDER_QUOTA_ENABLED", "true")
    policies = load_quota_policies(str(FIXTURE_YAML))
    mgr = ProviderQuotaManager(
        registry=QuotaPolicyRegistry(policies),
        redis_url="redis://127.0.0.1:1/0",
    )
    with pytest.raises(ProviderQuotaUnavailableError):
        await mgr.acquire(
            provider="google",
            model="gemini-3.1-flash-lite",
            quota_scope_id="gcp-project:test",
            estimated_input_tokens=1,
        )


@pytest.mark.asyncio
async def test_manager_acquire_with_fixture(monkeypatch):
    monkeypatch.setenv("PROVIDER_QUOTA_ENABLED", "true")
    policies = load_quota_policies(str(FIXTURE_YAML))
    client = redis_async.from_url(REDIS_URL, decode_responses=False)
    try:
        await client.ping()
    except Exception as e:
        await client.aclose()
        pytest.skip(str(e))
    await client.flushdb()
    store = RedisQuotaStore(client)
    mgr = ProviderQuotaManager(store=store, registry=QuotaPolicyRegistry(policies))
    lease, policy, res = await mgr.acquire(
        provider="google",
        model="gemini-3.1-flash-lite",
        quota_scope_id="gcp-project:test",
        estimated_input_tokens=10,
    )
    assert res.ok
    assert policy.max_in_flight == 3
    await mgr.release(
        provider="google",
        model="gemini-3.1-flash-lite",
        quota_scope_id="gcp-project:test",
        lease_id=lease,
        reserved_input_tokens=10,
        actual_prompt_tokens=10,
        allow_refund=True,
        policy=policy,
    )
    await client.aclose()
