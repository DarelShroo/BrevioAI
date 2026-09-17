"""Commercial acceptance matrix — limits from commercial_plans.yaml contract."""

from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest
from bson import ObjectId
from mongomock_motor import AsyncMongoMockClient

from core.brevio_api.models.errors.api_codes import ApiErrorCode
from core.brevio_api.services.billing.credit_service import CreditService
from core.brevio_api.services.billing.plan_registry import (
    clear_plan_registry_cache,
    get_plan,
    get_plan_registry,
    max_commercial_upload_bytes,
)
from core.brevio_api.services.billing.product_limit_service import (
    AdmissionRequest,
    DocumentMetrics,
    ProductLimitError,
    ProductLimitService,
)
from core.shared.enums.model import ModelType


EXPECTED = {
    "free": {
        "credits_per_period": 100,
        "rollover_max": 200,
        "documents_per_period": 10,
        "pages_per_document": 200,
        "pages_per_period": 1000,
        "bytes_per_document": 25 * 1024 * 1024,
        "bytes_per_audio": 50 * 1024 * 1024,
        "bytes_per_video": 250 * 1024 * 1024,
        "max_concurrent_jobs": 5,
        "byok_allowed": True,
    },
    "pro": {
        "credits_per_period": 4000,
        "rollover_max": 8000,
        "documents_per_period": 100,
        "pages_per_document": 1000,
        "pages_per_period": 10000,
        "bytes_per_document": 100 * 1024 * 1024,
        "bytes_per_audio": 250 * 1024 * 1024,
        "bytes_per_video": 2 * 1024 * 1024 * 1024,
        "max_concurrent_jobs": 20,
        "byok_allowed": True,
    },
    "business": {
        "credits_per_period": 20000,
        "rollover_max": 40000,
        "documents_per_period": 500,
        "pages_per_document": 5000,
        "pages_per_period": 50000,
        "bytes_per_document": 500 * 1024 * 1024,
        "bytes_per_audio": 1 * 1024 * 1024 * 1024,
        "bytes_per_video": 10 * 1024 * 1024 * 1024,
        "max_concurrent_jobs": 50,
        "byok_allowed": True,
    },
}


@pytest.fixture(autouse=True)
def _clear_plan_cache():
    clear_plan_registry_cache()
    yield
    clear_plan_registry_cache()


@pytest.fixture
def db():
    return AsyncMongoMockClient().get_database("commercial_acceptance")


def _req(user_id: str, job_id: str, docs, *, source_type="documents", has_byok=False):
    return AdmissionRequest(
        user_id=user_id,
        job_id=job_id,
        source_type=source_type,
        model=ModelType.QWEN3_8B,
        has_byok=has_byok,
        documents=docs,
    )


@pytest.mark.asyncio
async def test_commercial_matrix_matches_yaml():
    registry = get_plan_registry()
    for plan_id, expected in EXPECTED.items():
        plan = registry.plans[plan_id]
        for key, value in expected.items():
            assert getattr(plan, key) == value, f"{plan_id}.{key}"
        assert plan.byok_allowed is True
    assert max_commercial_upload_bytes() == EXPECTED["business"]["bytes_per_video"]


@pytest.mark.asyncio
@pytest.mark.parametrize("plan_id", ["free", "pro", "business"])
async def test_document_bytes_boundary(db, plan_id):
    products = ProductLimitService.from_db(db)
    await products.ensure_indexes()
    plan = get_plan(plan_id)
    uid = str(ObjectId())
    limit = plan.bytes_per_document
    await products.admit(
        _req(
            uid,
            f"ok-{ObjectId()}",
            [DocumentMetrics("ok.pdf", limit, 1)],
        ),
        plan=plan,
    )
    with pytest.raises(ProductLimitError) as exc:
        await products.admit(
            _req(
                uid,
                f"over-{ObjectId()}",
                [DocumentMetrics("big.pdf", limit + 1, 1)],
            ),
            plan=plan,
        )
    assert exc.value.code == ApiErrorCode.PLAN_BYTES_LIMIT.value


@pytest.mark.asyncio
@pytest.mark.parametrize("plan_id", ["free", "pro", "business"])
async def test_audio_video_bytes_boundary(db, plan_id):
    products = ProductLimitService.from_db(db)
    await products.ensure_indexes()
    plan = get_plan(plan_id)
    uid = str(ObjectId())

    await products.admit(
        _req(
            uid,
            f"audio-ok-{ObjectId()}",
            [DocumentMetrics("track.mp3", plan.bytes_per_audio, 0)],
            source_type="media",
        ),
        plan=plan,
    )
    with pytest.raises(ProductLimitError) as exc:
        await products.admit(
            _req(
                uid,
                f"audio-over-{ObjectId()}",
                [DocumentMetrics("track.mp3", plan.bytes_per_audio + 1, 0)],
                source_type="media",
            ),
            plan=plan,
        )
    assert exc.value.code == ApiErrorCode.PLAN_BYTES_LIMIT.value

    await products.admit(
        _req(
            uid,
            f"video-ok-{ObjectId()}",
            [DocumentMetrics("clip.mp4", plan.bytes_per_video, 0)],
            source_type="media",
        ),
        plan=plan,
    )
    with pytest.raises(ProductLimitError) as exc2:
        await products.admit(
            _req(
                uid,
                f"video-over-{ObjectId()}",
                [DocumentMetrics("clip.mp4", plan.bytes_per_video + 1, 0)],
                source_type="media",
            ),
            plan=plan,
        )
    assert exc2.value.code == ApiErrorCode.PLAN_BYTES_LIMIT.value


@pytest.mark.asyncio
@pytest.mark.parametrize("plan_id", ["free", "pro", "business"])
async def test_pages_per_document_boundary(db, plan_id):
    products = ProductLimitService.from_db(db)
    await products.ensure_indexes()
    plan = get_plan(plan_id)
    uid = str(ObjectId())
    await products.admit(
        _req(
            uid,
            f"pages-ok-{ObjectId()}",
            [DocumentMetrics("ok.pdf", 1000, plan.pages_per_document)],
        ),
        plan=plan,
    )
    with pytest.raises(ProductLimitError) as exc:
        await products.admit(
            _req(
                uid,
                f"pages-over-{ObjectId()}",
                [DocumentMetrics("big.pdf", 1000, plan.pages_per_document + 1)],
            ),
            plan=plan,
        )
    assert exc.value.code == ApiErrorCode.PLAN_PAGE_LIMIT.value


@pytest.mark.asyncio
@pytest.mark.parametrize("plan_id", ["free", "pro", "business"])
async def test_concurrent_jobs_boundary(db, plan_id):
    products = ProductLimitService.from_db(db)
    await products.ensure_indexes()
    plan = get_plan(plan_id)
    uid = str(ObjectId())
    for i in range(plan.max_concurrent_jobs):
        await products.admit(
            _req(uid, f"c-{i}-{ObjectId()}", [DocumentMetrics("a.txt", 10, 1)]),
            plan=plan,
        )
    with pytest.raises(ProductLimitError) as exc:
        await products.admit(
            _req(uid, f"c-over-{ObjectId()}", [DocumentMetrics("a.txt", 10, 1)]),
            plan=plan,
        )
    assert exc.value.code == ApiErrorCode.PLAN_CONCURRENCY_LIMIT.value


@pytest.mark.asyncio
@pytest.mark.parametrize("plan_id", ["free", "pro", "business"])
async def test_byok_allowed_on_all_plans(db, plan_id):
    products = ProductLimitService.from_db(db)
    await products.ensure_indexes()
    plan = get_plan(plan_id)
    assert plan.byok_allowed is True
    result = await products.admit(
        _req(
            str(ObjectId()),
            f"byok-{ObjectId()}",
            [DocumentMetrics("a.txt", 10, 1)],
            has_byok=True,
        ),
        plan=plan,
    )
    assert result.snapshot.byok_allowed is True


@pytest.mark.asyncio
async def test_free_period_grant_and_rollover(db):
    credits = CreditService.from_db(db)
    await credits.ensure_indexes()
    uid = str(ObjectId())
    plan = get_plan("free")

    account, created = await credits.apply_period_grant(
        uid,
        included=plan.credits_per_period,
        rollover_max=plan.rollover_max,
        grant_key="cal:free:2026-01-01",
    )
    assert created is True
    assert account.balance == 100

    # Consume 50 → remaining 50; renew → min(50+100, 200) = 150
    await credits.accounts.collection.update_one(
        {"user_id": ObjectId(uid)}, {"$set": {"balance": 50}}
    )
    account, created = await credits.apply_period_grant(
        uid,
        included=plan.credits_per_period,
        rollover_max=plan.rollover_max,
        grant_key="cal:free:2026-02-01",
    )
    assert created is True
    assert account.balance == 150

    # Remaining 150 → renew → min(150+100, 200) = 200 (not 250)
    account, created = await credits.apply_period_grant(
        uid,
        included=plan.credits_per_period,
        rollover_max=plan.rollover_max,
        grant_key="cal:free:2026-03-01",
    )
    assert created is True
    assert account.balance == 200

    # Idempotent same key
    account2, created2 = await credits.apply_period_grant(
        uid,
        included=plan.credits_per_period,
        rollover_max=plan.rollover_max,
        grant_key="cal:free:2026-03-01",
    )
    assert created2 is False
    assert account2.balance == 200


@pytest.mark.asyncio
async def test_pro_rollover_caps_at_8000(db):
    credits = CreditService.from_db(db)
    await credits.ensure_indexes()
    uid = str(ObjectId())
    plan = get_plan("pro")
    await credits.ensure_account(uid)
    await credits.accounts.collection.update_one(
        {"user_id": ObjectId(uid)}, {"$set": {"balance": 7000}}
    )
    account, created = await credits.apply_period_grant(
        uid,
        included=plan.credits_per_period,
        rollover_max=plan.rollover_max,
        grant_key="cal:pro:2026-04-01",
    )
    assert created is True
    assert account.balance == 8000


@pytest.mark.asyncio
async def test_period_grant_concurrent_idempotent(db):
    credits = CreditService.from_db(db)
    await credits.ensure_indexes()
    uid = str(ObjectId())
    plan = get_plan("free")
    await credits.ensure_account(uid)

    async def once():
        return await credits.apply_period_grant(
            uid,
            included=plan.credits_per_period,
            rollover_max=plan.rollover_max,
            grant_key="cal:free:race",
        )

    results = await asyncio.gather(*[once() for _ in range(20)])
    created_flags = [c for _, c in results]
    assert sum(1 for c in created_flags if c) == 1
    balance = await credits.get_balance(uid)
    assert balance == 100


@pytest.mark.asyncio
async def test_insufficient_credits_rejects_reservation(db):
    credits = CreditService.from_db(db)
    await credits.ensure_indexes()
    uid = str(ObjectId())
    await credits.ensure_account(uid)
    from core.brevio_api.models.errors.provider_errors import ProviderError

    with pytest.raises(ProviderError):
        await credits.reserve_for_job(
            user_id=uid,
            job_id=f"job-{ObjectId()}",
            amount=1,
            expected_amount=1,
        )


@pytest.mark.asyncio
async def test_documents_per_period_boundary_free(db):
    products = ProductLimitService.from_db(db)
    await products.ensure_indexes()
    plan = get_plan("free")
    uid = str(ObjectId())
    for i in range(plan.documents_per_period):
        jid = f"doc-{i}-{ObjectId()}"
        await products.admit(
            _req(uid, jid, [DocumentMetrics("a.txt", 10, 1)]), plan=plan
        )
        await products.commit_admission(jid)
    with pytest.raises(ProductLimitError) as exc:
        await products.admit(
            _req(uid, f"doc-over-{ObjectId()}", [DocumentMetrics("a.txt", 10, 1)]),
            plan=plan,
        )
    assert exc.value.code == ApiErrorCode.PLAN_DOCUMENT_LIMIT.value


@pytest.mark.asyncio
async def test_pages_per_period_independent_of_per_document(db):
    """Free: 200 pages/doc OK, but period cap 1000 still applies."""
    products = ProductLimitService.from_db(db)
    await products.ensure_indexes()
    plan = replace(get_plan("free"), pages_per_period=250, documents_per_period=10)
    uid = str(ObjectId())
    j1 = f"p1-{ObjectId()}"
    await products.admit(
        _req(uid, j1, [DocumentMetrics("a.pdf", 100, 200)]), plan=plan
    )
    await products.commit_admission(j1)
    with pytest.raises(ProductLimitError) as exc:
        await products.admit(
            _req(uid, f"p2-{ObjectId()}", [DocumentMetrics("b.pdf", 100, 51)]),
            plan=plan,
        )
    assert exc.value.code == ApiErrorCode.PLAN_PAGE_LIMIT.value
