"""FASE 3: credit reservation, ledger, settlement — concurrency & invariants."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from mongomock_motor import AsyncMongoMockClient

from core.brevio_api.models.billing.credit_models import (
    BillingMode,
    CreditAccount,
    LedgerReason,
    ReservationStatus,
    utcnow,
)
from core.brevio_api.models.errors.provider_errors import (
    ProviderError,
    ProviderErrorKind,
)
from core.brevio_api.services.billing.credit_service import CreditService
from core.shared.enums.model import ModelType


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client.get_database("credit_test")


@pytest.fixture
def user_id() -> str:
    return str(ObjectId())


@pytest.fixture
async def credits(db, user_id: str) -> CreditService:
    user = MagicMock()
    user.user_credit = 50
    user_repo = MagicMock()
    user_repo.get_user_by_field = AsyncMock(return_value=user)
    service = CreditService.from_db(db, user_repo=user_repo)
    await service.ensure_indexes()
    account = await service.ensure_account(user_id)
    # Force exact starting balance for concurrency tests.
    await service.accounts.collection.update_one(
        {"_id": ObjectId(str(account.id))},
        {"$set": {"balance": 50}},
    )
    return service


@pytest.mark.asyncio
async def test_concurrent_reservations_against_real_mongo():
    """Real MongoDB concurrency: 100×1 against balance=50 must yield exactly 50."""
    import os

    from motor.motor_asyncio import AsyncIOMotorClient

    uri = os.getenv(
        "FASE3_MONGO_URI",
        "mongodb://root:password@127.0.0.1:27017/brevio_fase3_credit?authSource=admin",
    )
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=3000)
    try:
        await client.admin.command("ping")
    except Exception as exc:
        pytest.skip(f"real mongo unavailable: {exc}")

    db = client.get_database("brevio_fase3_credit")
    # Isolate collections for this run.
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
    account = CreditAccount(user_id=ObjectId(uid), balance=50)
    await service.accounts.create(account)

    async def one(i: int):
        try:
            await service.reserve_for_job(
                user_id=uid,
                job_id=f"real-mongo-{i}-{ObjectId()}",
                amount=1,
                expected_amount=1,
                billing_mode=BillingMode.PLATFORM.value,
            )
            return True
        except ProviderError:
            return False

    for round_idx in range(2):
        await service.accounts.collection.update_one(
            {"user_id": ObjectId(uid)}, {"$set": {"balance": 50}}
        )
        await service.reservations.collection.delete_many({})
        await service.ledger.collection.delete_many({})
        outcomes = await asyncio.gather(*[one(i) for i in range(100)])
        ok = sum(1 for x in outcomes if x)
        bal = await service.get_balance(uid)
        assert ok == 50, f"round {round_idx}: successes={ok}"
        assert bal == 0, f"round {round_idx}: balance={bal}"

    client.close()


@pytest.mark.asyncio
async def test_balance_never_negative_invariant(credits: CreditService, user_id: str):
    updated = await credits.accounts.atomic_debit_if_available(user_id, 50)
    assert updated is not None
    assert updated.balance == 0
    failed = await credits.accounts.atomic_debit_if_available(user_id, 1)
    assert failed is None
    account = await credits.accounts.get_by_user_id(user_id)
    assert account is not None
    assert account.balance >= 0


@pytest.mark.asyncio
async def test_concurrent_reservations_respect_balance(
    credits: CreditService, user_id: str
):
    """100 concurrent 1-credit reserves against balance=50 → ≤50 success, balance≥0."""

    async def one(i: int):
        job_id = f"job-concurrent-{i}-{ObjectId()}"
        try:
            result = await credits.reserve_for_job(
                user_id=user_id,
                job_id=job_id,
                amount=1,
                expected_amount=1,
                billing_mode=BillingMode.PLATFORM.value,
            )
            return ("ok", result)
        except ProviderError as exc:
            assert exc.kind == ProviderErrorKind.INSUFFICIENT_CREDITS
            return ("fail", None)

    # Run several rounds to surface races under mongomock interleaving.
    for _round in range(3):
        # Reset balance and clear collections between rounds.
        await credits.accounts.collection.update_one(
            {"user_id": ObjectId(user_id)}, {"$set": {"balance": 50}}
        )
        await credits.reservations.collection.delete_many({})
        await credits.ledger.collection.delete_many({})
        await credits.settlements.collection.delete_many({})

        outcomes = await asyncio.gather(*[one(i) for i in range(100)])
        successes = [o for o in outcomes if o[0] == "ok"]
        failures = [o for o in outcomes if o[0] == "fail"]
        account = await credits.accounts.get_by_user_id(user_id)
        assert account is not None
        assert account.balance >= 0
        assert len(successes) == 50
        assert len(failures) == 50
        assert account.balance == 0


@pytest.mark.asyncio
async def test_double_settlement_is_idempotent(credits: CreditService, user_id: str):
    await credits.accounts.collection.update_one(
        {"user_id": ObjectId(user_id)}, {"$set": {"balance": 200}}
    )
    job_id = f"job-settle-{ObjectId()}"
    await credits.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=100,
        expected_amount=70,
        billing_mode=BillingMode.PLATFORM.value,
    )

    results = await asyncio.gather(
        *[credits.settle_job(job_id=job_id, consumed_credits=70) for _ in range(3)]
    )
    created_flags = [r.created for r in results]
    assert sum(1 for c in created_flags if c) == 1
    settlements = await credits.settlements.collection.count_documents(
        {"job_id": job_id}
    )
    assert settlements == 1
    settlement = next(r.settlement for r in results if r.created) 
    assert settlement.consumed_credits == 70
    assert settlement.released_credits == 30
    account = await credits.accounts.get_by_user_id(user_id)
    assert account is not None
    # Started 200, reserved 100 → 100, released 30 → 130. Net consumed 70.
    assert account.balance == 130
    assert account.balance >= 0


@pytest.mark.asyncio
async def test_double_release_is_idempotent(credits: CreditService, user_id: str):
    await credits.accounts.collection.update_one(
        {"user_id": ObjectId(user_id)}, {"$set": {"balance": 100}}
    )
    job_id = f"job-release-{ObjectId()}"
    reserved = await credits.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=40,
        expected_amount=40,
        billing_mode=BillingMode.PLATFORM.value,
    )
    before = await credits.get_balance(user_id)
    results = await asyncio.gather(
        *[
            credits.release_reservation(reserved.reservation)
            for _ in range(5)
        ]
    )
    assert all(r.status == ReservationStatus.RELEASED.value for r in results)
    after = await credits.get_balance(user_id)
    assert after == before + 40
    release_entries = await credits.ledger.collection.count_documents(
        {
            "reservation_id": ObjectId(str(reserved.reservation.id)),
            "reason": LedgerReason.RELEASE.value,
        }
    )
    assert release_entries == 1


@pytest.mark.asyncio
async def test_crash_reconciler_releases_expired_once(
    credits: CreditService, user_id: str
):
    await credits.accounts.collection.update_one(
        {"user_id": ObjectId(user_id)}, {"$set": {"balance": 80}}
    )
    job_id = f"job-crash-{ObjectId()}"
    reserved = await credits.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=25,
        expected_amount=25,
        billing_mode=BillingMode.PLATFORM.value,
    )
    # Simulate worker death: reservation expired, job FAILED.
    await credits.reservations.collection.update_one(
        {"_id": ObjectId(str(reserved.reservation.id))},
        {"$set": {"expires_at": utcnow() - timedelta(seconds=10)}},
    )

    async def lookup(_job_id: str):
        return "FAILED"

    stats1, stats2 = await asyncio.gather(
        credits.reconcile_expired_reservations(job_status_lookup=lookup),
        credits.reconcile_expired_reservations(job_status_lookup=lookup),
    )
    assert stats1["released"] + stats2["released"] == 1
    account = await credits.accounts.get_by_user_id(user_id)
    assert account is not None
    assert account.balance == 80
    reservation = await credits.reservations.get_by_job_id(job_id)
    assert reservation is not None
    assert reservation.status in (
        ReservationStatus.RELEASED.value,
        ReservationStatus.COMMITTED.value,
    )
    settlement = await credits.settlements.get_by_job_id(job_id)
    assert settlement is not None
    assert settlement.consumed_credits == 0
    assert settlement.released_credits == 25


@pytest.mark.asyncio
async def test_byok_reserves_credits_like_platform(credits: CreditService, user_id: str):
    await credits.accounts.collection.update_one(
        {"user_id": ObjectId(user_id)}, {"$set": {"balance": 50}}
    )
    job_id = f"job-byok-{ObjectId()}"
    result = await credits.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=50,
        expected_amount=50,
        billing_mode=BillingMode.BYOK.value,
    )
    assert result.reservation.amount == 50
    assert result.billing_mode == BillingMode.BYOK.value
    account = await credits.accounts.get_by_user_id(user_id)
    assert account is not None
    assert account.balance == 0


@pytest.mark.asyncio
async def test_byok_zero_balance_rejected(credits: CreditService, user_id: str):
    await credits.accounts.collection.update_one(
        {"user_id": ObjectId(user_id)}, {"$set": {"balance": 0}}
    )
    with pytest.raises(ProviderError) as exc:
        await credits.reserve_for_job(
            user_id=user_id,
            job_id=f"job-byok-empty-{ObjectId()}",
            amount=10,
            expected_amount=10,
            billing_mode=BillingMode.BYOK.value,
        )
    assert exc.value.kind == ProviderErrorKind.INSUFFICIENT_CREDITS


@pytest.mark.asyncio
async def test_platform_zero_balance_rejected_before_enqueue(
    credits: CreditService, user_id: str
):
    await credits.accounts.collection.update_one(
        {"user_id": ObjectId(user_id)}, {"$set": {"balance": 0}}
    )
    with pytest.raises(ProviderError) as exc:
        await credits.reserve_for_job(
            user_id=user_id,
            job_id=f"job-nocredit-{ObjectId()}",
            amount=10,
            expected_amount=10,
            billing_mode=BillingMode.PLATFORM.value,
        )
    assert exc.value.kind == ProviderErrorKind.INSUFFICIENT_CREDITS
    assert await credits.reservations.collection.count_documents({}) == 0


@pytest.mark.asyncio
async def test_reservation_idempotent_same_job(
    credits: CreditService, user_id: str
):
    await credits.accounts.collection.update_one(
        {"user_id": ObjectId(user_id)}, {"$set": {"balance": 100}}
    )
    job_id = f"job-idem-{ObjectId()}"
    first = await credits.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=20,
        expected_amount=10,
        billing_mode=BillingMode.PLATFORM.value,
    )
    second = await credits.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=20,
        expected_amount=10,
        billing_mode=BillingMode.PLATFORM.value,
    )
    assert first.created is True
    assert second.created is False
    assert str(first.reservation.id) == str(second.reservation.id)
    account = await credits.accounts.get_by_user_id(user_id)
    assert account is not None
    assert account.balance == 80


@pytest.mark.asyncio
async def test_ledger_append_only_no_update_helpers():
    assert not hasattr(CreditService, "update_ledger")
    assert not hasattr(CreditService, "delete_ledger")
    from core.brevio_api.repositories.billing.credit_repositories import (
        CreditLedgerRepository,
    )

    assert not hasattr(CreditLedgerRepository, "update")
    assert not hasattr(CreditLedgerRepository, "delete")
    assert hasattr(CreditLedgerRepository, "append")


@pytest.mark.asyncio
async def test_overrun_clamped_to_reserved(credits: CreditService, user_id: str):
    await credits.accounts.collection.update_one(
        {"user_id": ObjectId(user_id)}, {"$set": {"balance": 200}}
    )
    job_id = f"job-overrun-{ObjectId()}"
    await credits.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=100,
        expected_amount=80,
        billing_mode=BillingMode.PLATFORM.value,
    )
    result = await credits.settle_job(job_id=job_id, consumed_credits=130)
    assert result.settlement.consumed_credits == 100
    assert result.settlement.released_credits == 0
    assert result.settlement.overrun_detected is True


@pytest.mark.asyncio
async def test_compute_reservation_uses_maximum_for_platform():
    service = CreditService(
        MagicMock(), MagicMock(), MagicMock(), MagicMock()
    )
    reserved, expected = service.compute_reservation_amount(
        billing_mode=BillingMode.PLATFORM.value,
        maximum_credits=120,
        expected_credits=87,
    )
    assert reserved == 120
    assert expected == 87
    byok_r, byok_e = service.compute_reservation_amount(
        billing_mode=BillingMode.BYOK.value,
        maximum_credits=120,
        expected_credits=87,
    )
    assert byok_r == 120 and byok_e == 87
    local_r, local_e = service.compute_reservation_amount(
        billing_mode=BillingMode.LOCAL.value,
        maximum_credits=40,
        expected_credits=25,
    )
    assert local_r == 40 and local_e == 25


@pytest.mark.asyncio
async def test_resolve_billing_mode_local_and_byok():
    service = CreditService(
        MagicMock(), MagicMock(), MagicMock(), MagicMock()
    )
    assert (
        service.resolve_billing_mode(model=ModelType.QWEN3_8B, has_byok=False)
        == BillingMode.LOCAL.value
    )
    assert (
        service.resolve_billing_mode(model=ModelType.GPT_4O_MINI, has_byok=True)
        == BillingMode.BYOK.value
    )
    assert (
        service.resolve_billing_mode(model=ModelType.GPT_4O_MINI, has_byok=False)
        == BillingMode.PLATFORM.value
    )


@pytest.mark.asyncio
async def test_migration_from_user_credit_idempotent(db):
    uid = str(ObjectId())
    user = MagicMock()
    user.user_credit = 12.7
    user_repo = MagicMock()
    user_repo.get_user_by_field = AsyncMock(return_value=user)
    service = CreditService.from_db(db, user_repo=user_repo)
    await service.ensure_indexes()
    a1 = await service.ensure_account(uid)
    a2 = await service.ensure_account(uid)
    assert a1.balance == 12
    assert str(a1.id) == str(a2.id)
    count = await service.accounts.collection.count_documents(
        {"user_id": ObjectId(uid)}
    )
    assert count == 1


@pytest.mark.asyncio
async def test_corrupt_negative_user_credit_raises(db):
    uid = str(ObjectId())
    user = MagicMock()
    user.user_credit = -5.0
    user_repo = MagicMock()
    user_repo.get_user_by_field = AsyncMock(return_value=user)
    service = CreditService.from_db(db, user_repo=user_repo)
    await service.ensure_indexes()
    with pytest.raises(ValueError, match="negative"):
        await service.ensure_account(uid)


@pytest.mark.asyncio
async def test_failed_job_full_release(credits: CreditService, user_id: str):
    await credits.accounts.collection.update_one(
        {"user_id": ObjectId(user_id)}, {"$set": {"balance": 100}}
    )
    job_id = f"job-fail-{ObjectId()}"
    await credits.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=60,
        expected_amount=40,
        billing_mode=BillingMode.PLATFORM.value,
    )
    result = await credits.settle_job_failure(job_id)
    assert result.settlement.consumed_credits == 0
    assert result.settlement.released_credits == 60
    account = await credits.accounts.get_by_user_id(user_id)
    assert account is not None
    assert account.balance == 100
