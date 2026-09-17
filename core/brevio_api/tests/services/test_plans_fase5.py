"""FASE 5: plans, PlanSnapshot, product limits, concurrency."""

from __future__ import annotations

import asyncio
import os
from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from mongomock_motor import AsyncMongoMockClient

from core.brevio_api.models.billing.credit_models import BillingMode, CreditAccount
from core.brevio_api.models.errors.api_codes import ApiErrorCode
from core.brevio_api.services.billing.credit_service import CreditService
from core.brevio_api.services.billing.plan_registry import (
    clear_plan_registry_cache,
    default_plan,
    get_plan,
    get_plan_registry,
)
from core.brevio_api.services.billing.product_limit_service import (
    AdmissionRequest,
    DocumentMetrics,
    ProductLimitError,
    ProductLimitService,
    measure_documents,
)
from core.shared.enums.model import ModelType


@pytest.fixture(autouse=True)
def _clear_plan_cache():
    clear_plan_registry_cache()
    yield
    clear_plan_registry_cache()


@pytest.fixture
def db():
    return AsyncMongoMockClient().get_database("fase5_plans")


@pytest.fixture
def user_id() -> str:
    return str(ObjectId())


@pytest.fixture
async def products(db) -> ProductLimitService:
    svc = ProductLimitService.from_db(db)
    await svc.ensure_indexes()
    return svc


def _user(plan_id: str = "free", version: str = "1"):
    u = MagicMock()
    u.id = ObjectId()
    u.plan_id = plan_id
    u.plan_version = version
    return u


def _req(
    user_id: str,
    job_id: str,
    *,
    docs=None,
    source_type="documents",
    model=ModelType.QWEN3_8B,
    has_byok=False,
):
    return AdmissionRequest(
        user_id=user_id,
        job_id=job_id,
        source_type=source_type,
        model=model,
        has_byok=has_byok,
        documents=docs
        or [DocumentMetrics("a.txt", 100, 1)],
    )


@pytest.mark.asyncio
async def test_plan_registry_has_free_pro_business():
    registry = get_plan_registry()
    assert set(registry.plans) == {"free", "pro", "business"}
    assert default_plan().plan_id == "free"
    assert get_plan("pro").documents_per_period == 100
    assert get_plan("business").media_enabled is True
    assert registry.period_mode == "calendar_month"
    assert registry.plan_change_usage_policy == "keep_period_counters"


@pytest.mark.asyncio
async def test_plan_snapshot_frozen_after_plan_change(products, user_id):
    plan_v1 = get_plan("pro")
    job_id = f"job-snap-{ObjectId()}"
    result = await products.admit(_req(user_id, job_id), plan=plan_v1)
    assert result.snapshot.plan_id == "pro"
    assert result.snapshot.plan_version == "1"
    assert result.snapshot.documents_per_period == plan_v1.documents_per_period

    plan_v2 = replace(plan_v1, version="2", documents_per_period=999)
    again = await products.admit(_req(user_id, job_id), plan=plan_v2)
    assert again.snapshot.plan_version == "1"
    assert again.snapshot.documents_per_period == plan_v1.documents_per_period
    assert again.product_record.snapshot is not None
    assert again.product_record.snapshot.plan_version == "1"


@pytest.mark.asyncio
async def test_document_limit_reject(products):
    plan = get_plan("free")  # 10 docs / period
    uid = str(ObjectId())
    for i in range(10):
        jid = f"job-ok-{i}-{ObjectId()}"
        await products.admit(_req(uid, jid), plan=plan)
        await products.commit_admission(jid)
    with pytest.raises(ProductLimitError) as exc:
        await products.admit(_req(uid, f"job-over-{ObjectId()}"), plan=plan)
    assert exc.value.code == ApiErrorCode.PLAN_DOCUMENT_LIMIT.value


@pytest.mark.asyncio
async def test_page_limit_per_document(products, user_id):
    plan = get_plan("free")  # pages_per_document=200
    with pytest.raises(ProductLimitError) as exc:
        await products.admit(
            _req(
                user_id,
                f"job-pages-{ObjectId()}",
                docs=[DocumentMetrics("big.pdf", 1000, plan.pages_per_document + 1)],
            ),
            plan=plan,
        )
    assert exc.value.code == ApiErrorCode.PLAN_PAGE_LIMIT.value


@pytest.mark.asyncio
async def test_page_limit_exact_boundary_allowed(products, user_id):
    plan = get_plan("free")
    result = await products.admit(
        _req(
            user_id,
            f"job-pages-ok-{ObjectId()}",
            docs=[DocumentMetrics("ok.pdf", 1000, plan.pages_per_document)],
        ),
        plan=plan,
    )
    assert result.pages == plan.pages_per_document


@pytest.mark.asyncio
async def test_pages_per_period_reject(products):
    plan = replace(get_plan("pro"), pages_per_period=100, documents_per_period=1000)
    uid = str(ObjectId())
    jid = f"job-pperiod-{ObjectId()}"
    await products.admit(
        _req(uid, jid, docs=[DocumentMetrics("a.pdf", 100, 100)]),
        plan=plan,
    )
    await products.commit_admission(jid)
    with pytest.raises(ProductLimitError) as exc:
        await products.admit(
            _req(
                uid,
                f"job-pperiod2-{ObjectId()}",
                docs=[DocumentMetrics("b.pdf", 100, 1)],
            ),
            plan=plan,
        )
    assert exc.value.code == ApiErrorCode.PLAN_PAGE_LIMIT.value


@pytest.mark.asyncio
async def test_bytes_limit(products, user_id):
    plan = get_plan("free")
    with pytest.raises(ProductLimitError) as exc:
        await products.admit(
            _req(
                user_id,
                f"job-bytes-{ObjectId()}",
                docs=[DocumentMetrics("big.bin", plan.bytes_per_document + 1, 1)],
            ),
            plan=plan,
        )
    assert exc.value.code == ApiErrorCode.PLAN_BYTES_LIMIT.value


@pytest.mark.asyncio
async def test_period_admit_when_under_limit(products, user_id):
    plan = get_plan("free")
    result = await products.admit(_req(user_id, f"job-under-{ObjectId()}"), plan=plan)
    assert result.documents == 1
    usage = await products.periods.get_period(
        user_id, result.period_start, result.period_end
    )
    assert usage.documents_used == 1


@pytest.mark.asyncio
async def test_byok_zero_credits_still_consumes_documents(products, user_id):
    plan = get_plan("pro")
    job_id = f"job-byok-{ObjectId()}"
    result = await products.admit(
        _req(
            user_id,
            job_id,
            model=ModelType.GPT_4O_MINI,
            has_byok=True,
            docs=[DocumentMetrics("a.txt", 100, 2)],
        ),
        plan=plan,
    )
    assert result.documents == 1
    assert result.pages == 2
    await products.commit_admission(job_id)
    usage = await products.periods.get_period(
        user_id, result.period_start, result.period_end
    )
    assert usage is not None
    assert usage.documents_used == 1
    assert usage.credits_used == 0


@pytest.mark.asyncio
async def test_media_enabled_on_free(products, user_id):
    plan = get_plan("free")
    assert plan.media_enabled is True
    result = await products.admit(
        _req(
            user_id,
            f"job-media-{ObjectId()}",
            source_type="media",
            docs=[DocumentMetrics("a.mp3", 100, 0)],
        ),
        plan=plan,
    )
    assert result.documents == 1


@pytest.mark.asyncio
async def test_youtube_disabled_on_free(products, user_id):
    plan = get_plan("free")
    with pytest.raises(ProductLimitError) as exc:
        await products.admit(
            _req(
                user_id,
                f"job-yt-{ObjectId()}",
                source_type="youtube",
                docs=measure_documents([], source_type="youtube"),
            ),
            plan=plan,
        )
    assert exc.value.code == ApiErrorCode.YOUTUBE_DISABLED.value


@pytest.mark.asyncio
async def test_product_usage_idempotent_same_job(products, user_id):
    plan = get_plan("pro")
    job_id = f"job-idem-{ObjectId()}"
    req = _req(user_id, job_id)
    a = await products.admit(req, plan=plan)
    b = await products.admit(req, plan=plan)
    assert a.product_record.job_id == b.product_record.job_id
    usage = await products.periods.get_period(
        user_id, a.period_start, a.period_end
    )
    assert usage.documents_used == 1


@pytest.mark.asyncio
async def test_double_release_reconciler_safe(products, user_id):
    plan = get_plan("pro")
    job_id = f"job-rel-{ObjectId()}"
    result = await products.admit(_req(user_id, job_id), plan=plan)
    await products.release_admission(job_id)
    await products.release_admission(job_id)
    usage = await products.periods.get_period(
        user_id, result.period_start, result.period_end
    )
    assert usage.documents_used == 0
    assert usage.concurrent_jobs == 0


@pytest.mark.asyncio
async def test_credits_used_from_settlement_not_reservation(products, user_id):
    plan = get_plan("pro")
    job_id = f"job-cred-{ObjectId()}"
    result = await products.admit(_req(user_id, job_id), plan=plan)
    await products.commit_admission(job_id)
    usage = await products.periods.get_period(
        user_id, result.period_start, result.period_end
    )
    assert usage.credits_used == 0
    await products.record_settled_credits(
        job_id, 7, credits_limit=plan.rollover_max
    )
    await products.record_settled_credits(
        job_id, 7, credits_limit=plan.rollover_max
    )
    usage = await products.periods.get_period(
        user_id, result.period_start, result.period_end
    )
    assert usage.credits_used == 7


@pytest.mark.asyncio
async def test_model_not_funded_without_byok(products, user_id):
    plan = get_plan("free")
    with pytest.raises(ProductLimitError) as exc:
        await products.admit(
            _req(
                user_id,
                f"job-fund-{ObjectId()}",
                model=ModelType.GPT_4O_MINI,
                has_byok=False,
            ),
            plan=plan,
        )
    assert exc.value.code == ApiErrorCode.MODEL_NOT_FUNDED.value


@pytest.mark.asyncio
async def test_entitlements_shape(products):
    user = _user("pro")
    data = await products.entitlements(user)
    assert data["plan_id"] == "pro"
    assert "remaining" in data
    assert data["limits"]["documents_per_period"] == 100
    assert data["period_mode"] == "calendar_month"
    assert data["plan_change_usage_policy"] == "keep_period_counters"
    assert "retention_days" in data["limits"]
    assert "funds_all_models" in data["limits"]
    assert isinstance(data["limits"]["brevio_funded_models"], list)


async def _real_mongo(db_name: str):
    from motor.motor_asyncio import AsyncIOMotorClient

    uri = os.getenv(
        "FASE5_MONGO_URI",
        "mongodb://root:password@127.0.0.1:27017/?authSource=admin",
    )
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=3000)
    try:
        await client.admin.command("ping")
    except Exception as exc:
        client.close()
        pytest.skip(f"real mongo unavailable: {exc}")
    db = client.get_database(db_name)
    return client, db


@pytest.mark.asyncio
async def test_concurrent_product_limits_real_mongo():
    client, db = await _real_mongo("brevio_fase5_plans")
    try:
        for name in ("product_period_usage", "product_usage_records"):
            await db[name].delete_many({})

        svc = ProductLimitService.from_db(db)
        await svc.ensure_indexes()
        uid = str(ObjectId())
        limited = replace(
            get_plan("pro"),
            documents_per_period=50,
            pages_per_period=10_000,
            max_concurrent_jobs=200,
        )

        async def one(i: int) -> bool:
            try:
                await svc.admit(
                    _req(
                        uid,
                        f"real-{i}-{ObjectId()}",
                        docs=[DocumentMetrics(f"{i}.txt", 10, 1)],
                    ),
                    plan=limited,
                )
                return True
            except ProductLimitError:
                return False

        for round_idx in range(2):
            await db["product_period_usage"].delete_many({})
            await db["product_usage_records"].delete_many({})
            outcomes = await asyncio.gather(*[one(i) for i in range(100)])
            ok = sum(1 for x in outcomes if x)
            assert ok == 50, f"round {round_idx}: accepted={ok}"
            usage_docs = await db["product_period_usage"].find().to_list(10)
            assert usage_docs
            assert usage_docs[0]["documents_used"] == 50
    finally:
        client.close()


@pytest.mark.asyncio
async def test_combined_credits_and_product_limits_real_mongo():
    client, db = await _real_mongo("brevio_fase5_combo")
    try:
        for name in (
            "product_period_usage",
            "product_usage_records",
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
        credits = CreditService.from_db(db, user_repo=user_repo)
        await credits.ensure_indexes()
        await credits.accounts.create(CreditAccount(user_id=ObjectId(uid), balance=50))
        products = ProductLimitService.from_db(db)
        await products.ensure_indexes()
        limited = replace(
            get_plan("pro"),
            documents_per_period=50,
            pages_per_period=10_000,
            max_concurrent_jobs=200,
        )

        async def one(i: int) -> bool:
            job_id = f"combo-{i}-{ObjectId()}"
            try:
                await products.admit(
                    _req(
                        uid,
                        job_id,
                        docs=[DocumentMetrics(f"{i}.txt", 10, 1)],
                    ),
                    plan=limited,
                )
            except ProductLimitError:
                return False
            try:
                await credits.reserve_for_job(
                    user_id=uid,
                    job_id=job_id,
                    amount=1,
                    expected_amount=1,
                    billing_mode=BillingMode.PLATFORM.value,
                )
                return True
            except Exception:
                await products.release_admission(job_id)
                return False

        outcomes = await asyncio.gather(*[one(i) for i in range(100)])
        ok = sum(1 for x in outcomes if x)
        bal = await credits.get_balance(uid)
        usage = await db["product_period_usage"].find_one({"user_id": ObjectId(uid)})
        assert ok == 50
        assert bal == 0
        assert bal >= 0
        assert usage["documents_used"] == 50
    finally:
        client.close()
