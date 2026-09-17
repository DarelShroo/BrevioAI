"""FASE 8 attack / hardening regression suite.

Organized by threat class. Critical concurrency uses real Redis/Mongo when available.
"""

from __future__ import annotations

import asyncio
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from core.brevio_api.models.billing.credit_models import (
    BillingMode,
    CreditAccount,
    CreditReservation,
    JobSettlement,
    ReservationStatus,
    SettlementStatus,
    utcnow,
)
from core.brevio_api.services.billing.credit_service import CreditService
from core.brevio_api.services.billing.product_limit_service import (
    ProductLimitService,
    current_period_bounds,
)
from core.brevio_api.utils.upload_security import (
    assert_content_matches_extension,
    sanitize_upload_filename,
)
from core.shared.utils.youtube_url import normalize_youtube_url

# ---------------------------------------------------------------------------
# PATH / UPLOAD
# ---------------------------------------------------------------------------


def test_path_traversal_variants_sanitized() -> None:
    payloads = [
        "../../etc/passwd",
        "..\\..\\windows\\system32\\cmd.exe",
        "%2e%2e/%2e%2e/etc/passwd",
        "....//....//etc/passwd",
        "/absolute/path.pdf",
        "a/../../b.pdf",
        "file\x00.pdf",
    ]
    for raw in payloads:
        safe = sanitize_upload_filename(raw)
        assert "/" not in safe
        assert "\\" not in safe
        assert ".." not in safe
        assert "\x00" not in safe


def test_magic_bytes_rejects_extension_spoof() -> None:
    with pytest.raises(HTTPException) as exc:
        assert_content_matches_extension("malware.pdf", b"#!/bin/sh\necho pwned\n")
    assert exc.value.status_code == 400

    assert_content_matches_extension("ok.pdf", b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")

    with pytest.raises(HTTPException):
        assert_content_matches_extension("fake.docx", b"not-a-zip")

    with pytest.raises(HTTPException):
        assert_content_matches_extension("x.png", b"GIF89a....")


def test_magic_bytes_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UPLOAD_MAGIC_BYTES_ENABLED", "0")
    assert_content_matches_extension("spoof.pdf", b"not-a-pdf")


# ---------------------------------------------------------------------------
# SSRF / YOUTUBE
# ---------------------------------------------------------------------------


def test_ssrf_and_youtube_path_constraints() -> None:
    blocked = [
        "http://youtube.com/watch?v=x",
        "https://127.0.0.1/watch?v=x",
        "https://169.254.169.254/latest/meta-data/",
        "https://youtube.com.evil.com/watch?v=x",
        "https://user:pass@youtube.com/watch?v=x",
        "https://www.youtube.com/redirect?q=http://evil",
        "https://www.youtube.com/api/stats",
    ]
    for url in blocked:
        with pytest.raises(ValueError):
            normalize_youtube_url(url)

    assert normalize_youtube_url(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    ).startswith("https://www.youtube.com/watch")
    assert normalize_youtube_url("https://youtu.be/dQw4w9WgXcQ").startswith(
        "https://youtu.be/"
    )


# ---------------------------------------------------------------------------
# BILLING ATTACKS
# ---------------------------------------------------------------------------


@pytest.fixture
def credit_db():
    return AsyncMongoMockClient().get_database("fase8_credit")


@pytest.fixture
async def credit_svc(credit_db) -> CreditService:
    user = MagicMock()
    user.user_credit = 100
    user_repo = MagicMock()
    user_repo.get_user_by_field = AsyncMock(return_value=user)
    svc = CreditService.from_db(credit_db, user_repo=user_repo)
    await svc.ensure_indexes()
    return svc


@pytest.mark.asyncio
async def test_billing_double_settlement_idempotent(credit_svc: CreditService) -> None:
    uid = str(ObjectId())
    account = CreditAccount(user_id=ObjectId(uid), balance=100)
    await credit_svc.accounts.create(account)
    job_id = str(ObjectId())
    await credit_svc.reserve_for_job(
        user_id=uid,
        job_id=job_id,
        amount=40,
        expected_amount=40,
        billing_mode=BillingMode.PLATFORM.value,
    )
    r1 = await credit_svc.settle_job(job_id=job_id, consumed_credits=10)
    r2 = await credit_svc.settle_job(job_id=job_id, consumed_credits=10)
    assert r1.created is True
    assert r2.created is False
    assert str(r1.settlement.id) == str(r2.settlement.id)
    bal = await credit_svc.accounts.get_by_user_id(uid)
    assert bal is not None
    assert bal.balance == 90  # 100 - 40 + 30 released


@pytest.mark.asyncio
async def test_billing_settlement_crash_recovery_refunds(
    credit_svc: CreditService,
) -> None:
    """Settlement row exists while reservation still PENDING → finalize recovers."""
    uid = str(ObjectId())
    await credit_svc.accounts.create(CreditAccount(user_id=ObjectId(uid), balance=50))
    job_id = str(ObjectId())
    reserved = await credit_svc.reserve_for_job(
        user_id=uid,
        job_id=job_id,
        amount=20,
        expected_amount=20,
        billing_mode=BillingMode.PLATFORM.value,
    )
    reservation = reserved.reservation
    # Simulate crash after settlement insert, before finalize.
    settlement = JobSettlement(
        job_id=job_id,
        user_id=ObjectId(uid),
        reservation_id=reservation.id,
        billing_mode=BillingMode.PLATFORM.value,
        reserved_credits=20,
        consumed_credits=5,
        released_credits=15,
        status=SettlementStatus.SETTLED.value,
    )
    await credit_svc.settlements.create(settlement)
    # Reservation still PENDING, balance still 30 (50-20).
    bal = await credit_svc.accounts.get_by_user_id(uid)
    assert bal is not None and bal.balance == 30

    result = await credit_svc.settle_job(job_id=job_id, consumed_credits=5)
    assert result.created is False
    res = await credit_svc.reservations.get_by_job_id(job_id)
    assert res is not None
    assert res.status in {
        ReservationStatus.COMMITTED.value,
        ReservationStatus.RELEASED.value,
    }
    bal2 = await credit_svc.accounts.get_by_user_id(uid)
    assert bal2 is not None
    assert bal2.balance == 45  # 30 + 15 released once


@pytest.mark.asyncio
async def test_billing_double_release_idempotent(credit_svc: CreditService) -> None:
    uid = str(ObjectId())
    await credit_svc.accounts.create(CreditAccount(user_id=ObjectId(uid), balance=30))
    job_id = str(ObjectId())
    reserved = await credit_svc.reserve_for_job(
        user_id=uid,
        job_id=job_id,
        amount=10,
        expected_amount=10,
        billing_mode=BillingMode.PLATFORM.value,
    )
    await credit_svc.release_reservation(reserved.reservation)
    await credit_svc.release_reservation(reserved.reservation)
    bal = await credit_svc.accounts.get_by_user_id(uid)
    assert bal is not None and bal.balance == 30


@pytest.mark.asyncio
async def test_ledger_is_append_only(credit_svc: CreditService) -> None:
    assert not hasattr(credit_svc.ledger, "update")
    assert not hasattr(credit_svc.ledger, "delete")
    assert callable(credit_svc.ledger.append)


@pytest.mark.asyncio
async def test_concurrent_reservations_real_mongo_invariant() -> None:
    from motor.motor_asyncio import AsyncIOMotorClient

    uri = os.getenv(
        "FASE3_MONGO_URI",
        "mongodb://root:password@127.0.0.1:27017/brevio_fase8_attack?authSource=admin",
    )
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=3000)
    try:
        await client.admin.command("ping")
    except Exception as exc:
        pytest.skip(f"real mongo unavailable: {exc}")

    db = client.get_database("brevio_fase8_attack")
    for name in (
        "credit_accounts",
        "credit_reservations",
        "credit_ledger",
        "job_settlements",
    ):
        await db[name].delete_many({})

    uid = str(ObjectId())
    user = MagicMock()
    user.user_credit = 0
    user_repo = MagicMock()
    user_repo.get_user_by_field = AsyncMock(return_value=user)
    service = CreditService.from_db(db, user_repo=user_repo)
    await service.ensure_indexes()
    await service.accounts.create(CreditAccount(user_id=ObjectId(uid), balance=50))

    async def one(i: int) -> bool:
        try:
            await service.reserve_for_job(
                user_id=uid,
                job_id=f"fase8-{i}-{ObjectId()}",
                amount=1,
                expected_amount=1,
                billing_mode=BillingMode.PLATFORM.value,
            )
            return True
        except Exception:
            return False

    results = await asyncio.gather(*[one(i) for i in range(100)])
    assert sum(1 for ok in results if ok) == 50
    bal = await service.accounts.get_by_user_id(uid)
    assert bal is not None and bal.balance == 0
    client.close()


# ---------------------------------------------------------------------------
# PRODUCT LIMITS / PERIOD / CAPACITY / RATE LIMIT
# ---------------------------------------------------------------------------


def _redis_or_skip():
    import redis

    url = os.getenv("FASE7_REDIS_URI", "redis://127.0.0.1:6380/14")
    try:
        client = redis.Redis.from_url(url, decode_responses=True)
        client.ping()
        return url, client
    except Exception as exc:
        pytest.skip(f"real redis unavailable: {exc}")


def test_rolling_days_period_is_bucketed(monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import datetime, timezone

    from core.brevio_api.services.billing import plan_registry as pr
    from core.brevio_api.services.billing.plan_registry import (
        PlanRegistryConfig,
        PricingDisplayConfig,
    )
    from core.brevio_api.services.billing.product_limit_service import (
        current_period_bounds as bounds,
    )

    fake = PlanRegistryConfig(
        period_mode="rolling_days",
        rolling_days=30,
        plan_change_usage_policy="keep_period_counters",
        default_plan_id="free",
        plans={},
        pricing=PricingDisplayConfig(
            currency="EUR",
            show_billing_toggle=False,
            annual_discount_percent=0,
            sales_email="support@brevio.com",
            highlighted_plan_id="pro",
        ),
    )
    monkeypatch.setattr(pr, "get_plan_registry", lambda: fake)
    a = bounds(now=datetime(2026, 3, 15, 10, 30, tzinfo=timezone.utc))
    b = bounds(now=datetime(2026, 3, 15, 23, 59, tzinfo=timezone.utc))
    assert a == b
    assert a[0].hour == 0 and a[0].minute == 0


def test_rate_limit_multi_process_shared_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.brevio_api.services.anti_abuse.config import BucketConfig
    from core.brevio_api.services.anti_abuse.rate_limiter import DistributedRateLimiter

    url, client = _redis_or_skip()
    monkeypatch.setenv("ANTI_ABUSE_REDIS_URL", url)
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "1")
    client.flushdb()
    bucket = BucketConfig("fase8", 50, 60, fail_closed=True)

    def worker(n: int) -> int:
        lim = DistributedRateLimiter(
            __import__("redis").Redis.from_url(url, decode_responses=True)
        )
        ok = 0
        for _ in range(n):
            result = lim.hit(identity="ip:10.0.0.1", bucket=bucket)
            if result.allowed:
                ok += 1
        return ok

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(worker, 50)
        b = pool.submit(worker, 50)
        allowed = a.result() + b.result()
    assert allowed == 50


def test_capacity_acquire_respects_global_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.brevio_api.services.capacity.capacity_store import CapacityStore

    url, client = _redis_or_skip()
    monkeypatch.setenv("CAPACITY_REDIS_URL", url)
    monkeypatch.setenv("GLOBAL_MAX_CONCURRENT_JOBS", "5")
    client.flushdb()
    store = CapacityStore(client)

    acquired = 0
    holders: list[str] = []
    for i in range(20):
        job_id = f"cap-{i}"
        result = store.acquire(
            job_id=job_id, user_id="u1", user_max=100, global_max=5
        )
        if result.ok:
            acquired += 1
            holders.append(job_id)
    assert acquired == 5
    for job_id in holders:
        store.release(job_id=job_id, user_id="u1")
    assert store.acquire(
        job_id="cap-re", user_id="u1", user_max=100, global_max=5
    ).ok


@pytest.mark.asyncio
async def test_commit_admission_idempotent_concurrency() -> None:
    from core.brevio_api.services.billing.plan_registry import (
        clear_plan_registry_cache,
        get_plan,
    )
    from core.brevio_api.services.billing.product_limit_service import (
        AdmissionRequest,
        DocumentMetrics,
    )
    from core.shared.enums.model import ModelType

    clear_plan_registry_cache()
    db = AsyncMongoMockClient().get_database("fase8_plans")
    svc = ProductLimitService.from_db(db)
    await svc.ensure_indexes()
    uid = str(ObjectId())
    jid = str(ObjectId())
    plan = get_plan("free")
    await svc.admit(
        AdmissionRequest(
            user_id=uid,
            job_id=jid,
            source_type="documents",
            model=ModelType.QWEN3_8B,
            has_byok=False,
            documents=[DocumentMetrics("a.pdf", 100, 1)],
        ),
        plan=plan,
    )
    await svc.commit_admission(jid)
    period_start, period_end = current_period_bounds()
    period = await svc.periods.get_period(uid, period_start, period_end)
    concurrent_after_first = period.concurrent_jobs if period else 0
    await svc.commit_admission(jid)
    await svc.commit_admission(jid)
    period2 = await svc.periods.get_period(uid, period_start, period_end)
    assert period2 is not None
    assert period2.concurrent_jobs == concurrent_after_first
    assert period2.concurrent_jobs >= 0
    clear_plan_registry_cache()


# ---------------------------------------------------------------------------
# AUTH / SESSION
# ---------------------------------------------------------------------------


def test_access_token_revoked_after_logout(monkeypatch: pytest.MonkeyPatch) -> None:
    url, client = _redis_or_skip()
    monkeypatch.setenv("ANTI_ABUSE_REDIS_URL", url)
    from core.brevio_api.services.session_revocation import (
        deny_access_jti,
        is_access_revoked,
    )
    from core.brevio_api.services.token_service import TokenService

    tokens = TokenService()
    access = tokens.create_access_token({"id": str(ObjectId())})
    payload = tokens.validate_access_token(access)
    assert not is_access_revoked(payload)
    deny_access_jti(str(payload["jti"]))
    assert is_access_revoked(payload)


def test_refresh_rotate_requires_expected_jti() -> None:
    """Repository filter includes jti+hash — concurrent loser gets None."""
    from core.brevio_api.repositories.refresh_session_repository import (
        RefreshSessionRepository,
    )

    # Signature regression: expected_jti / expected_token_hash required.
    import inspect

    sig = inspect.signature(RefreshSessionRepository.rotate)
    assert "expected_jti" in sig.parameters
    assert "expected_token_hash" in sig.parameters


# ---------------------------------------------------------------------------
# IDEMPOTENCY / CONFIG / SECRETS
# ---------------------------------------------------------------------------


def test_production_rejects_wildcard_cors_and_missing_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.brevio_api.utils.security_runtime import assert_secure_runtime_config

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("API_KEY", "production-api-key-value-24chars-min")
    monkeypatch.setenv("SECRET_TOKEN_KEY", "production-jwt-secret-value-32chars-min!!")
    monkeypatch.setenv(
        "CREDENTIAL_ENCRYPTION_KEY",
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    )
    monkeypatch.setenv("CORS_ORIGINS", "*")
    monkeypatch.setenv("TRUSTED_PROXY", "172.28.0.0/16")
    monkeypatch.setenv("REDIS_PASSWORD", "production-redis-pass-16+")
    with pytest.raises(RuntimeError):
        assert_secure_runtime_config()


def test_env_example_has_no_live_secrets() -> None:
    root = Path(__file__).resolve().parents[4]
    example = (root / ".env.example").read_text(encoding="utf-8")
    assert "sk-live" not in example.lower()
    assert "BEGIN PRIVATE KEY" not in example
    # Placeholders are OK; real-looking long random secrets are not expected here.
    assert "local_api_key_123" in example or "API_KEY=" in example


def test_docker_compose_does_not_publish_mongo_redis() -> None:
    root = Path(__file__).resolve().parents[4]
    text = (root / "docker-compose.yml").read_text(encoding="utf-8")
    # Host publish would look like "27017:27017" / "6379:6379"
    assert "27017:27017" not in text
    assert "6379:6379" not in text
    assert '"27017"' in text
    assert "subnet: 172.28.0.0/16" in text
    assert "deploy/redis/entrypoint.sh" in text
    assert "REDIS_PASSWORD" in text


def test_security_headers_middleware_present() -> None:
    from core.brevio_api.__main__ import app

    client = TestClient(app)
    response = client.get("/__fase8_missing__")
    assert response.headers.get("x-content-type-options") == "nosniff"
