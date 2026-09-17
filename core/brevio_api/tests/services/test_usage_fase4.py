"""FASE 4: UsageRecord → CostRecord → real settlement tests."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from mongomock_motor import AsyncMongoMockClient

from core.brevio.services.provider_quota.usage_normalize import normalize_provider_usage
from core.brevio_api.models.billing.credit_models import BillingMode
from core.brevio_api.models.billing.usage_models import UsageAttemptStatus, UsageSource
from core.brevio_api.services.billing.credit_service import CreditService
from core.brevio_api.services.billing.usage_service import (
    ProviderAttemptEvent,
    UsageBillingService,
)
from core.shared.enums.model import ModelType
from core.shared.utils.pricing_registry import (
    PricingSnapshot,
    calculate_actual_provider_cost,
    calculate_credits,
    convert_to_platform_currency,
)


@pytest.fixture
def db():
    return AsyncMongoMockClient().get_database("fase4_usage")


@pytest.fixture
def user_id() -> str:
    return str(ObjectId())


@pytest.fixture
async def services(db, user_id: str):
    user = MagicMock()
    user.user_credit = 500
    user_repo = MagicMock()
    user_repo.get_user_by_field = AsyncMock(return_value=user)
    credits = CreditService.from_db(db, user_repo=user_repo)
    await credits.ensure_indexes()
    account = await credits.ensure_account(user_id)
    await credits.accounts.collection.update_one(
        {"_id": ObjectId(str(account.id))}, {"$set": {"balance": 500}}
    )
    usage = UsageBillingService.from_db(db, credit_service=credits)
    await usage.ensure_indexes()
    return credits, usage


def _openai_response(*, prompt: int, completion: int, cached: int = 0, rid="req-1"):
    details = SimpleNamespace(cached_tokens=cached) if cached else None
    usage = SimpleNamespace(
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=prompt + completion,
        prompt_tokens_details=details,
        completion_tokens_details=None,
    )
    choice = SimpleNamespace(finish_reason="stop")
    return SimpleNamespace(id=rid, usage=usage, choices=[choice])


@pytest.mark.asyncio
async def test_normalize_openai_usage_real():
    resp = _openai_response(prompt=100, completion=40, cached=10)
    n = normalize_provider_usage(resp)
    assert n.usage_source == "REAL"
    assert n.input_tokens == 100
    assert n.output_tokens == 40
    assert n.cached_input_tokens == 10
    assert n.provider_request_id == "req-1"


@pytest.mark.asyncio
async def test_normalize_missing_usage_unavailable():
    n = normalize_provider_usage(SimpleNamespace(id="x", choices=[]))
    assert n.usage_source == "UNAVAILABLE"
    assert n.input_tokens == 0


@pytest.mark.asyncio
async def test_provider_success_creates_usage_and_cost(services, user_id: str):
    credits, usage = services
    job_id = f"job-ok-{ObjectId()}"
    await credits.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=120,
        expected_amount=87,
        billing_mode=BillingMode.PLATFORM.value,
    )
    record = await usage.record_provider_attempt(
        ProviderAttemptEvent(
            job_id=job_id,
            user_id=user_id,
            provider="openai",
            model=ModelType.GPT_4O_MINI.value,
            phase="MAP",
            retry_index=0,
            chunk_id="0",
            credential_scope="platform",
            status=UsageAttemptStatus.SUCCESS.value,
            response=_openai_response(prompt=2000, completion=500),
        )
    )
    assert record.usage_source == UsageSource.REAL.value
    assert record.input_tokens == 2000
    cost = await usage.costs.get_by_usage_id(str(record.id))
    assert cost is not None
    assert cost.pricing_version
    assert cost.credits >= 0


@pytest.mark.asyncio
async def test_retry_attempts_both_registered(services, user_id: str):
    _, usage = services
    job_id = f"job-retry-{ObjectId()}"
    await usage.record_provider_attempt(
        ProviderAttemptEvent(
            job_id=job_id,
            user_id=user_id,
            provider="openai",
            model=ModelType.GPT_4O_MINI.value,
            phase="MAP",
            retry_index=0,
            chunk_id="1",
            credential_scope="platform",
            status=UsageAttemptStatus.ERROR.value,
            response=_openai_response(prompt=100, completion=0, rid="a"),
        )
    )
    await usage.record_provider_attempt(
        ProviderAttemptEvent(
            job_id=job_id,
            user_id=user_id,
            provider="openai",
            model=ModelType.GPT_4O_MINI.value,
            phase="MAP",
            retry_index=1,
            chunk_id="1",
            credential_scope="platform",
            status=UsageAttemptStatus.SUCCESS.value,
            response=_openai_response(prompt=110, completion=40, rid="b"),
        )
    )
    rows = await usage.usage.list_by_job(job_id)
    assert len(rows) == 2
    assert {r.retry_index for r in rows} == {0, 1}


@pytest.mark.asyncio
async def test_fallback_providers_both_counted(services, user_id: str):
    credits, usage = services
    job_id = f"job-fb-{ObjectId()}"
    await credits.accounts.collection.update_one(
        {"user_id": ObjectId(user_id)}, {"$set": {"balance": 500}}
    )
    await credits.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=200,
        expected_amount=100,
        billing_mode=BillingMode.PLATFORM.value,
    )
    await usage.record_provider_attempt(
        ProviderAttemptEvent(
            job_id=job_id,
            user_id=user_id,
            provider="openai",
            model=ModelType.GPT_4O_MINI.value,
            phase="MAP",
            retry_index=0,
            chunk_id="0",
            credential_scope="platform",
            status=UsageAttemptStatus.ERROR.value,
            response=_openai_response(prompt=2000, completion=100),
        )
    )
    await usage.record_provider_attempt(
        ProviderAttemptEvent(
            job_id=job_id,
            user_id=user_id,
            provider="google",
            model=ModelType.GEMINI_3_1_FLASH_LITE.value,
            phase="MAP",
            retry_index=0,
            chunk_id="0",
            credential_scope="platform",
            status=UsageAttemptStatus.SUCCESS.value,
            response=_openai_response(prompt=2500, completion=200),
            is_fallback=True,
        )
    )
    consumed = await usage.calculate_job_consumed_credits(job_id)
    costs = await usage.costs.list_by_job(job_id)
    assert len(costs) == 2
    assert consumed == sum(c.credits for c in costs)
    assert consumed > costs[1].credits  # includes failed openai attempt


@pytest.mark.asyncio
async def test_cost_with_controlled_pricing():
    snap = PricingSnapshot(
        provider="openai",
        model="test",
        input_price_per_million=1.0,
        output_price_per_million=2.0,
        cached_input_price_per_million=0.1,
        currency="USD",
        effective_from="2026-01-01",
        pricing_version="test-v1",
        platform_currency="EUR",
        fx_rate_to_platform=1.0,
        commercial_margin=0.0,
        credit_unit_value=0.01,
        minimum_credits=1,
    )
    # 1000 input (100 cached) + 500 output
    # billable_input=900 * 1 + 100*0.1 + 500*2 = 900+10+1000 = 1910 / 1e6
    cost = calculate_actual_provider_cost(
        input_tokens=1000,
        output_tokens=500,
        cached_input_tokens=100,
        snapshot=snap,
    )
    assert abs(cost - 0.00191) < 1e-9
    platform = convert_to_platform_currency(cost, snap)
    credits = calculate_credits(platform, snap)
    assert credits == 1  # ceil(0.00191/0.01)=1


@pytest.mark.asyncio
async def test_settlement_reserved_120_actual_usage(services, user_id: str, monkeypatch):
    credits, usage = services
    job_id = f"job-settle-{ObjectId()}"
    await credits.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=120,
        expected_amount=87,
        billing_mode=BillingMode.PLATFORM.value,
    )

    async def fake_credits(job_id: str) -> int:
        return 87

    monkeypatch.setattr(usage, "calculate_job_consumed_credits", fake_credits)
    result = await usage.settle_job_from_usage(job_id)
    assert result.created is True
    assert result.settlement.consumed_credits == 87
    assert result.settlement.released_credits == 33
    bal = await credits.get_balance(user_id)
    # 500 - 120 reserved + 33 released = 413
    assert bal == 413


@pytest.mark.asyncio
async def test_zero_usage_full_release(services, user_id: str):
    credits, usage = services
    job_id = f"job-zero-{ObjectId()}"
    await credits.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=120,
        expected_amount=50,
        billing_mode=BillingMode.PLATFORM.value,
    )
    result = await usage.settle_job_from_usage(job_id)
    assert result.settlement.consumed_credits == 0
    assert result.settlement.released_credits == 120
    assert await credits.get_balance(user_id) == 500


@pytest.mark.asyncio
async def test_overrun_clamp(services, user_id: str, monkeypatch):
    credits, usage = services
    job_id = f"job-over-{ObjectId()}"
    await credits.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=100,
        expected_amount=80,
        billing_mode=BillingMode.PLATFORM.value,
    )

    async def fake_credits(job_id: str) -> int:
        return 130

    monkeypatch.setattr(usage, "calculate_job_consumed_credits", fake_credits)
    result = await usage.settle_job_from_usage(job_id)
    assert result.settlement.consumed_credits == 100
    assert result.settlement.released_credits == 0
    assert result.settlement.overrun_detected is True
    assert result.settlement.overrun_requested == 130


@pytest.mark.asyncio
async def test_double_settlement_idempotent(services, user_id: str, monkeypatch):
    credits, usage = services
    job_id = f"job-dbl-{ObjectId()}"
    await credits.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=100,
        expected_amount=70,
        billing_mode=BillingMode.PLATFORM.value,
    )

    async def fake_credits(job_id: str) -> int:
        return 70

    monkeypatch.setattr(usage, "calculate_job_consumed_credits", fake_credits)
    results = await asyncio.gather(
        *[usage.settle_job_from_usage(job_id) for _ in range(3)]
    )
    assert sum(1 for r in results if r.created) == 1
    assert await credits.settlements.collection.count_documents({"job_id": job_id}) == 1


@pytest.mark.asyncio
async def test_usage_attempt_idempotent_no_duplicate(services, user_id: str):
    _, usage = services
    job_id = f"job-idem-{ObjectId()}"
    event = ProviderAttemptEvent(
        job_id=job_id,
        user_id=user_id,
        provider="openai",
        model=ModelType.GPT_4O_MINI.value,
        phase="REDUCE",
        retry_index=0,
        chunk_id="final",
        credential_scope="platform",
        status=UsageAttemptStatus.SUCCESS.value,
        response=_openai_response(prompt=50, completion=20),
    )
    a = await usage.record_provider_attempt(event)
    b = await usage.record_provider_attempt(event)
    assert str(a.id) == str(b.id)
    assert await usage.usage.collection.count_documents({"job_id": job_id}) == 1
    assert await usage.costs.collection.count_documents({"job_id": job_id}) == 1


@pytest.mark.asyncio
async def test_crash_between_usage_and_settlement_reconciles(
    services, user_id: str
):
    credits, usage = services
    job_id = f"job-crash-{ObjectId()}"
    await credits.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=80,
        expected_amount=40,
        billing_mode=BillingMode.PLATFORM.value,
    )
    await usage.record_provider_attempt(
        ProviderAttemptEvent(
            job_id=job_id,
            user_id=user_id,
            provider="openai",
            model=ModelType.GPT_4O_MINI.value,
            phase="MAP",
            retry_index=0,
            chunk_id="0",
            credential_scope="platform",
            status=UsageAttemptStatus.SUCCESS.value,
            response=_openai_response(prompt=500, completion=100),
        )
    )
    # Crash before settle — reconciler path
    r1 = await credits.settle_from_usage(job_id)
    r2 = await credits.settle_from_usage(job_id)
    assert r1.created is True
    assert r2.created is False
    assert await credits.settlements.collection.count_documents({"job_id": job_id}) == 1
    consumed = r1.settlement.consumed_credits
    assert consumed >= 0
    assert r1.settlement.released_credits == 80 - consumed
    assert await credits.get_balance(user_id) == 500 - consumed


@pytest.mark.asyncio
async def test_byok_usage_consumes_brevio_credits(services, user_id: str):
    credits, usage = services
    job_id = f"job-byok-{ObjectId()}"
    await credits.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=50,
        expected_amount=50,
        billing_mode=BillingMode.BYOK.value,
    )
    await usage.record_provider_attempt(
        ProviderAttemptEvent(
            job_id=job_id,
            user_id=user_id,
            provider="openai",
            model=ModelType.GPT_4O_MINI.value,
            phase="MAP",
            retry_index=0,
            chunk_id="0",
            credential_scope="user",
            status=UsageAttemptStatus.SUCCESS.value,
            response=_openai_response(prompt=2000, completion=500),
        )
    )
    consumed = await usage.calculate_job_consumed_credits(job_id)
    assert consumed > 0
    result = await usage.settle_job_from_usage(job_id)
    assert result.settlement.consumed_credits == consumed
    assert await credits.get_balance(user_id) == 500 - consumed
    rows = await usage.usage.list_by_job(job_id)
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_executor_records_retries(db, user_id: str):
    import httpx
    from openai import RateLimitError

    from core.brevio.services.provider_quota.executor import ProviderCallExecutor
    from core.brevio.services.provider_quota.policy import DEFAULT_RETRY_ONLY_POLICY
    from core.brevio_api.models.billing.credit_models import CreditAccount

    credits = CreditService.from_db(db)
    await credits.ensure_indexes()
    await credits.accounts.create(
        CreditAccount(user_id=ObjectId(user_id), balance=100)
    )
    usage = UsageBillingService.from_db(db, credit_service=credits)
    await usage.ensure_indexes()

    calls = {"n": 0}

    def _429():
        req = httpx.Request("POST", "https://example.com")
        resp = httpx.Response(
            429,
            request=req,
            headers={"retry-after": "0"},
            json={"error": {"message": "rate"}},
        )
        return RateLimitError(
            "429", response=resp, body={"error": {"message": "rate"}}
        )

    async def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise _429()
        return _openai_response(prompt=10, completion=5, rid="ok")

    policy = DEFAULT_RETRY_ONLY_POLICY
    mgr = MagicMock()
    mgr.resolve_policy = MagicMock(return_value=policy)
    mgr.acquire = AsyncMock(return_value=("lease", policy, None))
    mgr.release = AsyncMock()
    mgr.apply_cooldown = AsyncMock()
    mgr.cooldown_remaining_seconds = AsyncMock(return_value=0.0)

    ex = ProviderCallExecutor(quota_manager=mgr)
    job_id = f"job-ex-{ObjectId()}"
    ex.bind_billing_context(
        job_id=job_id,
        user_id=user_id,
        credential_scope="platform",
        usage_sink=usage,
    )
    await ex.execute(
        flaky,
        provider="openai",
        model=ModelType.GPT_4O_MINI.value,
        quota_scope_id="platform",
        phase="MAP",
        estimated_input_tokens=10,
        chunk_id="0",
    )
    rows = await usage.usage.list_by_job(job_id)
    assert len(rows) >= 2
    assert any(r.status == "ERROR" for r in rows)
    assert any(r.status == "SUCCESS" for r in rows)
