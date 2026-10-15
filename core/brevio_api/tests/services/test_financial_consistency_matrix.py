"""Comprehensive Financial Consistency and State Transition Matrix (FASE B).

Tests 20 critical scenarios on credit reservations, settlement, refunds,
worker crashes, idempotency, and ledger balance invariants.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from mongomock_motor import AsyncMongoMockClient

from core.brevio_api.models.billing.credit_models import (
    BillingMode,
    CreditAccount,
    CreditLedgerEntry,
    CreditReservation,
    JobSettlement,
    LedgerReason,
    ReservationStatus,
    SettlementStatus,
    utcnow,
)
from core.brevio_api.models.errors.provider_errors import (
    ProviderError,
    ProviderErrorKind,
)
from core.brevio_api.repositories.billing.credit_repositories import (
    CreditAccountRepository,
    CreditLedgerRepository,
    CreditReservationRepository,
    JobSettlementRepository,
)
from core.brevio_api.services.billing.credit_service import CreditService
from core.brevio_api.services.billing.product_limit_service import ProductLimitService
from core.brevio_api.services.brevio_service import BrevioService
from core.shared.enums.job_status import JobPhase, JobStatus


@pytest.fixture
def mock_db():
    client = AsyncMongoMockClient()
    return client.get_database("financial_matrix_test")


@pytest.fixture
def user_id() -> str:
    return str(ObjectId())


@pytest.fixture
async def credit_svc(mock_db, user_id: str) -> CreditService:
    user = MagicMock()
    user.user_credit = 200
    user_repo = MagicMock()
    user_repo.get_user_by_field = AsyncMock(return_value=user)
    service = CreditService.from_db(mock_db, user_repo=user_repo)
    await service.ensure_indexes()
    account = await service.ensure_account(user_id)
    await service.accounts.collection.update_one(
        {"_id": ObjectId(str(account.id))},
        {"$set": {"balance": 200}},
    )
    return service


async def _assert_ledger_invariant(credit_svc: CreditService, user_id: str):
    """Invariant: current balance exactly equals the sum of all immutable ledger deltas."""
    account = await credit_svc.accounts.get_by_user_id(user_id)
    assert account is not None
    entries = await credit_svc.ledger.collection.find({"user_id": ObjectId(user_id)}).to_list(1000)
    net_ledger = sum(int(e.get("delta", 0)) for e in entries)
    assert account.balance == net_ledger, (
        f"Ledger invariant violated: balance={account.balance} != net_ledger({net_ledger})"
    )


# Scenario 1: Documento vacío -> Zero charge, full refund
@pytest.mark.asyncio
async def test_scenario_01_empty_document_settles_zero(credit_svc: CreditService, user_id: str):
    job_id = f"job-empty-{ObjectId()}"
    await credit_svc.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=50,
        expected_amount=30,
        billing_mode=BillingMode.PLATFORM.value,
    )
    # Pipeline raises early DirectoryManagerError / empty document
    res = await credit_svc.settle_job(job_id=job_id, consumed_credits=0, metadata={"reason": "empty_document"})
    assert res.settlement.consumed_credits == 0
    assert res.settlement.released_credits == 50
    account = await credit_svc.accounts.get_by_user_id(user_id)
    assert account.balance == 200
    await _assert_ledger_invariant(credit_svc, user_id)


# Scenario 2: Documento corrupto -> Full release
@pytest.mark.asyncio
async def test_scenario_02_corrupt_document_full_release(credit_svc: CreditService, user_id: str):
    job_id = f"job-corrupt-{ObjectId()}"
    await credit_svc.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=60,
        expected_amount=40,
        billing_mode=BillingMode.PLATFORM.value,
    )
    res = await credit_svc.settle_job_failure(job_id)
    assert res.settlement.consumed_credits == 0
    assert res.settlement.released_credits == 60
    account = await credit_svc.accounts.get_by_user_id(user_id)
    assert account.balance == 200
    await _assert_ledger_invariant(credit_svc, user_id)


# Scenario 3: Documento sin texto extraíble -> Full release
@pytest.mark.asyncio
async def test_scenario_03_no_extractable_text_refunds(credit_svc: CreditService, user_id: str):
    job_id = f"job-notext-{ObjectId()}"
    await credit_svc.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=40,
        expected_amount=25,
        billing_mode=BillingMode.PLATFORM.value,
    )
    res = await credit_svc.settle_job(job_id=job_id, consumed_credits=0, metadata={"reason": "no_text"})
    assert res.settlement.released_credits == 40
    account = await credit_svc.accounts.get_by_user_id(user_id)
    assert account.balance == 200
    await _assert_ledger_invariant(credit_svc, user_id)


# Scenario 4: Error del proveedor LLM -> Full release of unconsumed
@pytest.mark.asyncio
async def test_scenario_04_provider_error_settles_cleanly(credit_svc: CreditService, user_id: str):
    job_id = f"job-llmerr-{ObjectId()}"
    await credit_svc.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=80,
        expected_amount=50,
        billing_mode=BillingMode.PLATFORM.value,
    )
    # LLM 500 error triggered during processing
    res = await credit_svc.settle_job_failure(job_id)
    assert res.settlement.consumed_credits == 0
    assert res.settlement.released_credits == 80
    account = await credit_svc.accounts.get_by_user_id(user_id)
    assert account.balance == 200
    await _assert_ledger_invariant(credit_svc, user_id)


# Scenario 5: Respuesta incompleta del proveedor -> Quality rejected -> Full release
@pytest.mark.asyncio
async def test_scenario_05_incomplete_truncated_response_refunded(credit_svc: CreditService, user_id: str):
    job_id = f"job-trunc-{ObjectId()}"
    await credit_svc.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=70,
        expected_amount=40,
        billing_mode=BillingMode.PLATFORM.value,
    )
    res = await credit_svc.settle_job(job_id=job_id, consumed_credits=0, metadata={"reason": "truncated_tail"})
    assert res.settlement.consumed_credits == 0
    assert res.settlement.released_credits == 70
    account = await credit_svc.accounts.get_by_user_id(user_id)
    assert account.balance == 200
    await _assert_ledger_invariant(credit_svc, user_id)


# Scenario 6: Respuesta rechazada por evaluador de calidad -> Full release
@pytest.mark.asyncio
async def test_scenario_06_quality_gate_rejected_refunds(credit_svc: CreditService, user_id: str):
    job_id = f"job-qgate-{ObjectId()}"
    await credit_svc.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=55,
        expected_amount=35,
        billing_mode=BillingMode.PLATFORM.value,
    )
    res = await credit_svc.settle_job(job_id=job_id, consumed_credits=0, metadata={"reason": "artifact_invalid"})
    assert res.settlement.released_credits == 55
    account = await credit_svc.accounts.get_by_user_id(user_id)
    assert account.balance == 200
    await _assert_ledger_invariant(credit_svc, user_id)


# Scenario 7: Fallo durante generación del PDF -> Settled cleanly without double charge
@pytest.mark.asyncio
async def test_scenario_07_pdf_generation_failure_handling(credit_svc: CreditService, user_id: str):
    job_id = f"job-pdf-{ObjectId()}"
    await credit_svc.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=50,
        expected_amount=30,
        billing_mode=BillingMode.PLATFORM.value,
    )
    # If PDF fails after successful summary, consumed credits match usage
    res = await credit_svc.settle_job(job_id=job_id, consumed_credits=30, metadata={"note": "pdf_failed"})
    assert res.settlement.consumed_credits == 30
    assert res.settlement.released_credits == 20
    account = await credit_svc.accounts.get_by_user_id(user_id)
    assert account.balance == 170
    await _assert_ledger_invariant(credit_svc, user_id)


# Scenario 8: Cancelación antes de iniciar el procesamiento -> Full release
@pytest.mark.asyncio
async def test_scenario_08_cancellation_before_processing(credit_svc: CreditService, user_id: str):
    job_id = f"job-cancel-early-{ObjectId()}"
    res = await credit_svc.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=45,
        expected_amount=25,
        billing_mode=BillingMode.PLATFORM.value,
    )
    # Cancelled while QUEUED
    updated_res = await credit_svc.release_reservation(res.reservation, reason=LedgerReason.RELEASE.value)
    assert updated_res.status == ReservationStatus.RELEASED.value
    account = await credit_svc.accounts.get_by_user_id(user_id)
    assert account.balance == 200
    await _assert_ledger_invariant(credit_svc, user_id)


# Scenario 9: Cancelación durante el procesamiento -> Full release of reserved
@pytest.mark.asyncio
async def test_scenario_09_cancellation_during_processing(credit_svc: CreditService, user_id: str):
    job_id = f"job-cancel-mid-{ObjectId()}"
    res = await credit_svc.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=65,
        expected_amount=40,
        billing_mode=BillingMode.PLATFORM.value,
    )
    # Cancelled while PROCESSING
    settle = await credit_svc.settle_job(job_id=job_id, consumed_credits=0, metadata={"reason": "cancelled_by_user"})
    assert settle.settlement.consumed_credits == 0
    assert settle.settlement.released_credits == 65
    account = await credit_svc.accounts.get_by_user_id(user_id)
    assert account.balance == 200
    await _assert_ledger_invariant(credit_svc, user_id)


# Scenario 10: Caída de worker tras reservar créditos -> Reconciled past TTL
@pytest.mark.asyncio
async def test_scenario_10_worker_crash_reconciled(credit_svc: CreditService, user_id: str):
    job_id = f"job-crash-{ObjectId()}"
    res = await credit_svc.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=50,
        expected_amount=30,
        billing_mode=BillingMode.PLATFORM.value,
    )
    # Force expiration in DB
    await credit_svc.reservations.collection.update_one(
        {"_id": ObjectId(str(res.reservation.id))},
        {"$set": {"expires_at": utcnow() - timedelta(minutes=5)}},
    )
    async def lookup(jid: str):
        return "FAILED"

    stats = await credit_svc.reconcile_expired_reservations(job_status_lookup=lookup)
    account = await credit_svc.accounts.get_by_user_id(user_id)
    assert account.balance == 200
    await _assert_ledger_invariant(credit_svc, user_id)


# Scenario 11: Caída tras guardar artefacto -> Settled from usage
@pytest.mark.asyncio
async def test_scenario_11_crash_after_artifact_settles_usage(credit_svc: CreditService, user_id: str):
    job_id = f"job-postartifact-{ObjectId()}"
    await credit_svc.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=50,
        expected_amount=25,
        billing_mode=BillingMode.PLATFORM.value,
    )
    # Settle with actual usage 25
    res = await credit_svc.settle_job(job_id=job_id, consumed_credits=25)
    assert res.settlement.consumed_credits == 25
    assert res.settlement.released_credits == 25
    account = await credit_svc.accounts.get_by_user_id(user_id)
    assert account.balance == 175
    await _assert_ledger_invariant(credit_svc, user_id)


# Scenario 12: Caída durante liquidación de créditos -> CAS refund_applied completes once
@pytest.mark.asyncio
async def test_scenario_12_crash_during_settlement_cas_idempotent(credit_svc: CreditService, user_id: str):
    job_id = f"job-crash-settle-{ObjectId()}"
    res = await credit_svc.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=80,
        expected_amount=50,
        billing_mode=BillingMode.PLATFORM.value,
    )
    # Insert settlement record as if crash happened before _finalize_reservation
    settlement = JobSettlement(
        job_id=job_id,
        user_id=ObjectId(user_id),
        reservation_id=res.reservation.id,
        billing_mode=BillingMode.PLATFORM.value,
        reserved_credits=80,
        consumed_credits=30,
        released_credits=50,
        status=SettlementStatus.SETTLED.value,
    )
    await credit_svc.settlements.create(settlement)

    # First recovery call
    await credit_svc._finalize_reservation_after_settlement(res.reservation, settlement)
    account = await credit_svc.accounts.get_by_user_id(user_id)
    assert account.balance == 170  # 200 - 80 + 50 = 170

    # Redelivery / duplicate recovery call
    await credit_svc._finalize_reservation_after_settlement(res.reservation, settlement)
    account_again = await credit_svc.accounts.get_by_user_id(user_id)
    assert account_again.balance == 170  # Exactly the same, no double refund!
    await _assert_ledger_invariant(credit_svc, user_id)


# Scenario 13: Reintento de un trabajo ya completado -> Idempotent
@pytest.mark.asyncio
async def test_scenario_13_completed_job_retry_is_idempotent(credit_svc: CreditService, user_id: str):
    job_id = f"job-completed-retry-{ObjectId()}"
    await credit_svc.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=40,
        expected_amount=20,
        billing_mode=BillingMode.PLATFORM.value,
    )
    res1 = await credit_svc.settle_job(job_id=job_id, consumed_credits=20)
    assert res1.created is True
    res2 = await credit_svc.settle_job(job_id=job_id, consumed_credits=20)
    assert res2.created is False
    assert str(res2.settlement.id) == str(res1.settlement.id)
    account = await credit_svc.accounts.get_by_user_id(user_id)
    assert account.balance == 180
    await _assert_ledger_invariant(credit_svc, user_id)


# Scenario 14: Reintento de un reembolso -> No double refund
@pytest.mark.asyncio
async def test_scenario_14_retry_of_refund_no_double_credit(credit_svc: CreditService, user_id: str):
    job_id = f"job-refund-retry-{ObjectId()}"
    res = await credit_svc.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=50,
        expected_amount=25,
        billing_mode=BillingMode.PLATFORM.value,
    )
    # First release
    await credit_svc.release_reservation(res.reservation)
    account = await credit_svc.accounts.get_by_user_id(user_id)
    assert account.balance == 200

    # Second release call
    await credit_svc.release_reservation(res.reservation)
    account = await credit_svc.accounts.get_by_user_id(user_id)
    assert account.balance == 200  # Still 200!
    await _assert_ledger_invariant(credit_svc, user_id)


# Scenario 15: Dos workers intentando procesar el mismo trabajo -> Exclusive claim
@pytest.mark.asyncio
async def test_scenario_15_concurrent_claim_queued_job_mutually_exclusive(mock_db):
    """Atomic find_one_and_update guarantees only 1 worker claims QUEUED job."""
    from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository
    repo = FolderEntryRepository(mock_db["folder_entries"])
    job_id = f"job-race-claim-{ObjectId()}"
    await repo.collection.insert_one({
        "_id": ObjectId(),
        "job_id": job_id,
        "job_status": JobStatus.QUEUED.value,
        "job_phase": JobPhase.QUEUED.value,
    })

    async def claim_worker(worker_id: str):
        return await repo.collection.find_one_and_update(
            {"job_id": job_id, "job_status": JobStatus.QUEUED.value},
            {"$set": {"job_status": JobStatus.PROCESSING.value, "worker_id": worker_id}},
        )

    results = await asyncio.gather(claim_worker("worker-1"), claim_worker("worker-2"))
    claimed = [r for r in results if r is not None]
    assert len(claimed) == 1, "Exactly one worker must claim the job"


# Scenario 16: Dos solicitudes simultáneas con la misma clave de idempotencia / job_id
@pytest.mark.asyncio
async def test_scenario_16_duplicate_reservation_idempotency(credit_svc: CreditService, user_id: str):
    job_id = f"job-dup-idempotency-{ObjectId()}"
    res1, res2 = await asyncio.gather(
        credit_svc.reserve_for_job(
            user_id=user_id,
            job_id=job_id,
            amount=40,
            expected_amount=20,
            billing_mode=BillingMode.PLATFORM.value,
        ),
        credit_svc.reserve_for_job(
            user_id=user_id,
            job_id=job_id,
            amount=40,
            expected_amount=20,
            billing_mode=BillingMode.PLATFORM.value,
        ),
    )
    # One is created=True, the other is created=False returning the existing one
    assert (res1.created and not res2.created) or (res2.created and not res1.created)
    assert str(res1.reservation.id) == str(res2.reservation.id)
    account = await credit_svc.accounts.get_by_user_id(user_id)
    assert account.balance == 160  # Debited exactly once (200 - 40 = 160)
    await _assert_ledger_invariant(credit_svc, user_id)


# Scenario 17: Reconciliación de trabajos antiguos -> Converges
@pytest.mark.asyncio
async def test_scenario_17_reconcile_ancient_pending_jobs(credit_svc: CreditService, user_id: str):
    job_id = f"job-ancient-{ObjectId()}"
    res = await credit_svc.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=30,
        expected_amount=15,
        billing_mode=BillingMode.PLATFORM.value,
    )
    await credit_svc.reservations.collection.update_one(
        {"_id": ObjectId(str(res.reservation.id))},
        {"$set": {"expires_at": utcnow() - timedelta(days=2)}},
    )
    async def lookup(jid: str):
        return None  # Missing from active table -> treated as abandoned

    await credit_svc.reconcile_expired_reservations(job_status_lookup=lookup)
    account = await credit_svc.accounts.get_by_user_id(user_id)
    assert account.balance == 200
    await _assert_ledger_invariant(credit_svc, user_id)


# Scenario 18: Fallo temporal de MongoDB durante settle -> Retry succeeds idempotently
@pytest.mark.asyncio
async def test_scenario_18_transient_mongo_failure_recovery(credit_svc: CreditService, user_id: str):
    job_id = f"job-transient-mongo-{ObjectId()}"
    await credit_svc.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=50,
        expected_amount=30,
        billing_mode=BillingMode.PLATFORM.value,
    )
    # Simulate first attempt failing with an exception before settle commit
    with patch.object(credit_svc.settlements, "create", side_effect=RuntimeError("connection dropped")):
        with pytest.raises(RuntimeError):
            await credit_svc.settle_job(job_id=job_id, consumed_credits=30)

    # Retry when connection is restored
    res = await credit_svc.settle_job(job_id=job_id, consumed_credits=30)
    assert res.settlement.consumed_credits == 30
    assert res.settlement.released_credits == 20
    account = await credit_svc.accounts.get_by_user_id(user_id)
    assert account.balance == 170
    await _assert_ledger_invariant(credit_svc, user_id)


# Scenario 19: Fallo temporal de Redis -> Overrun and safety policies enforce invariants
@pytest.mark.asyncio
async def test_scenario_19_overrun_policy_clamps_or_rejects(credit_svc: CreditService, user_id: str):
    job_id = f"job-overrun-{ObjectId()}"
    await credit_svc.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=50,
        expected_amount=30,
        billing_mode=BillingMode.PLATFORM.value,
    )
    # Requested consumed 80 > reserved 50 -> clamped to 50 under default policy
    res = await credit_svc.settle_job(job_id=job_id, consumed_credits=80)
    assert res.settlement.consumed_credits == 50
    assert res.settlement.overrun_detected is True
    account = await credit_svc.accounts.get_by_user_id(user_id)
    assert account.balance == 150  # Clamped to reserved 50
    await _assert_ledger_invariant(credit_svc, user_id)


# Scenario 20: Repetición de un mensaje o tarea -> Zero side-effects
@pytest.mark.asyncio
async def test_scenario_20_duplicate_task_redelivery(credit_svc: CreditService, user_id: str):
    job_id = f"job-redelivery-{ObjectId()}"
    await credit_svc.reserve_for_job(
        user_id=user_id,
        job_id=job_id,
        amount=60,
        expected_amount=40,
        billing_mode=BillingMode.PLATFORM.value,
    )
    # Execution 1 finishes
    res1 = await credit_svc.settle_job(job_id=job_id, consumed_credits=40)
    balance_after_1 = (await credit_svc.accounts.get_by_user_id(user_id)).balance

    # Redelivered task runs settle again
    res2 = await credit_svc.settle_job(job_id=job_id, consumed_credits=40)
    balance_after_2 = (await credit_svc.accounts.get_by_user_id(user_id)).balance

    assert balance_after_1 == balance_after_2 == 160
    assert res2.created is False
    await _assert_ledger_invariant(credit_svc, user_id)
