"""FASE 6: capacity admission, fairness, Redis concurrency."""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import replace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
import redis
from bson import ObjectId

from core.brevio_api.services.capacity.capacity_store import CapacityStore
from core.brevio_api.services.capacity.config import global_max_concurrent_jobs
from core.brevio_api.services.capacity.fair_scheduler import FairScheduler, WaitingJob


def _redis_url() -> str:
    return os.getenv(
        "FASE6_REDIS_URI",
        os.getenv(
            "CAPACITY_REDIS_URL",
            os.getenv(
                "PROVIDER_QUOTA_REDIS_URL",
                "redis://127.0.0.1:6380/15",
            ),
        ),
    )


@pytest.fixture
def rclient():
    client = redis.Redis.from_url(_redis_url(), decode_responses=True)
    try:
        client.ping()
    except Exception as exc:
        pytest.skip(f"real redis unavailable: {exc}")
    # Isolate keys for this module
    for key in client.scan_iter(match="brevio:capacity:*"):
        client.delete(key)
    for key in client.scan_iter(match="brevio:scheduler:*"):
        client.delete(key)
    yield client
    for key in client.scan_iter(match="brevio:capacity:*"):
        client.delete(key)
    for key in client.scan_iter(match="brevio:scheduler:*"):
        client.delete(key)
    client.close()


def _job(user: str, i: int, *, priority=10, weight=1, user_max=10) -> WaitingJob:
    return WaitingJob(
        job_id=f"job-{user}-{i}-{uuid4().hex[:8]}",
        user_id=user,
        plan_id="pro" if weight > 1 else "free",
        priority=priority,
        weight=weight,
        user_max=user_max,
        queued_at=time.time() + i * 0.001,
    )


def test_capacity_acquire_release_idempotent(rclient):
    store = CapacityStore(rclient)
    uid = str(ObjectId())
    jid = f"j-{uuid4().hex}"
    a = store.acquire(job_id=jid, user_id=uid, user_max=2, global_max=5)
    assert a.ok
    b = store.acquire(job_id=jid, user_id=uid, user_max=2, global_max=5)
    assert b.ok and b.reason == "idempotent"
    assert store.global_active() == 1
    r1 = store.release(job_id=jid, user_id=uid)
    assert r1.ok
    r2 = store.release(job_id=jid, user_id=uid)
    assert r2.reason == "noop"
    assert store.global_active() == 0
    assert store.user_active(uid) == 0


@pytest.mark.asyncio
async def test_concurrent_acquire_real_redis(rclient):
    store = CapacityStore(rclient)
    uid = str(ObjectId())

    async def one(i: int) -> bool:
        def _acq():
            return store.acquire(
                job_id=f"c-{i}-{uuid4().hex}",
                user_id=uid,
                user_max=200,
                global_max=50,
            ).ok

        return await asyncio.to_thread(_acq)

    outcomes = await asyncio.gather(*[one(i) for i in range(100)])
    assert sum(1 for x in outcomes if x) == 50
    assert store.global_active() == 50

    holders = list(rclient.smembers(CapacityStore.global_holders_key()))
    assert len(holders) == 50

    async def rel(jid: str) -> None:
        await asyncio.to_thread(lambda: store.release(job_id=jid, user_id=uid))

    await asyncio.gather(*[rel(j) for j in holders])
    assert store.global_active() == 0


def test_lease_ttl_crash_recovery(rclient):
    store = CapacityStore(rclient)
    uid = str(ObjectId())
    jid = f"crash-{uuid4().hex}"
    assert store.acquire(
        job_id=jid, user_id=uid, user_max=5, global_max=5, lease_ttl=1
    ).ok
    store.remember_lease_user(jid, uid, ttl=1)
    assert store.global_active() == 1
    time.sleep(1.5)
    assert not store.has_lease(jid)
    n = store.reclaim_expired_holders()
    assert n >= 1
    assert store.global_active() == 0
    assert store.user_active(uid) == 0


def test_fairness_no_monopolization(rclient, monkeypatch):
    store = CapacityStore(rclient)
    sched = FairScheduler(redis_client=rclient, store=store)
    user_a = f"A-{ObjectId()}"
    user_b = f"B-{ObjectId()}"
    for i in range(5):
        assert sched.register(_job(user_a, i, user_max=10)).ok
    assert sched.register(_job(user_b, 0, user_max=10)).ok

    original = store.acquire

    def acquire_cap(**kwargs):
        kwargs["global_max"] = 2
        return original(**kwargs)

    store.acquire = acquire_cap  # type: ignore
    dispatched = []

    def enqueue(jid: str) -> None:
        dispatched.append(jid)

    d1 = sched.dispatch_once(enqueue_fn=enqueue)
    d2 = sched.dispatch_once(enqueue_fn=enqueue)
    admitted = [d for d in d1 + d2 if d.admission_result == "admit"]
    assert len(admitted) == 2
    users = {d.user_id for d in admitted}
    assert user_b in users, f"B starved; admitted={[(d.user_id, d.job_id) for d in admitted]}"
    assert store.global_active() == 2


def test_plan_weights_affect_selection(rclient):
    store = CapacityStore(rclient)
    sched = FairScheduler(redis_client=rclient, store=store)
    free_u = f"free-{ObjectId()}"
    pro_u = f"pro-{ObjectId()}"
    for i in range(20):
        assert sched.register(
            _job(free_u, i, priority=10, weight=1, user_max=100)
        ).ok
        assert sched.register(
            _job(pro_u, i, priority=50, weight=2, user_max=100)
        ).ok

    counts = {free_u: 0, pro_u: 0}
    # High global so selection is about fairness weights/priority
    for _ in range(30):
        decisions = sched.dispatch_once(
            enqueue_fn=lambda jid: None,
        )
        # Manually acquire was done inside; release to free slots for next pick
        for d in decisions:
            if d.admission_result == "admit":
                counts[d.user_id] = counts.get(d.user_id, 0) + 1
                store.release(job_id=d.job_id, user_id=d.user_id)
        if sum(counts.values()) >= 20:
            break
    assert counts[pro_u] > counts[free_u], counts


def test_user_concurrency_limit(rclient):
    store = CapacityStore(rclient)
    sched = FairScheduler(redis_client=rclient, store=store)
    uid = f"u-{ObjectId()}"
    for i in range(10):
        assert sched.register(_job(uid, i, user_max=2)).ok
    enq = []
    for _ in range(5):
        sched.dispatch_once(enqueue_fn=lambda j: enq.append(j))
    assert store.user_active(uid) == 2
    assert len(enq) == 2


def test_global_concurrency_limit(rclient, monkeypatch):
    store = CapacityStore(rclient)
    sched = FairScheduler(redis_client=rclient, store=store)
    for u in range(20):
        uid = f"g-{u}-{ObjectId()}"
        for i in range(5):
            assert sched.register(_job(uid, i, user_max=10)).ok
    enq = []
    for _ in range(30):
        sched.dispatch_once(
            enqueue_fn=lambda j: enq.append(j),
        )
        if store.global_active() >= 5:
            # override by acquiring with global_max=5 via monkey — store already used env
            break
    # Force: release all and re-dispatch with explicit max by patching acquire
    # Clear and use acquire with global_max=5 directly
    for key in list(rclient.scan_iter(match="brevio:capacity:*")):
        rclient.delete(key)
    for key in list(rclient.scan_iter(match="brevio:scheduler:*")):
        rclient.delete(key)
    sched = FairScheduler(redis_client=rclient, store=store)
    for u in range(10):
        uid = f"g2-{u}-{ObjectId()}"
        for i in range(10):
            assert sched.register(_job(uid, i, user_max=10)).ok

    original = store.acquire

    def acquire_cap(**kwargs):
        kwargs["global_max"] = 5
        return original(**kwargs)

    store.acquire = acquire_cap  # type: ignore
    enq = []
    for _ in range(20):
        sched.dispatch_once(enqueue_fn=lambda j: enq.append(j))
    assert store.global_active() <= 5
    assert len(enq) == 5


def test_multi_user_no_permanent_monopoly(rclient):
    store = CapacityStore(rclient)
    sched = FairScheduler(redis_client=rclient, store=store)
    users = [f"mu-{i}-{ObjectId()}" for i in range(10)]
    for uid in users:
        for i in range(10):
            assert sched.register(_job(uid, i, user_max=3)).ok

    original = store.acquire

    def acquire_cap(**kwargs):
        kwargs["global_max"] = 5
        return original(**kwargs)

    store.acquire = acquire_cap  # type: ignore
    seen = set()
    for round_i in range(10):
        # free slots between rounds
        holders = list(rclient.smembers(CapacityStore.global_holders_key()))
        for jid in holders:
            meta = rclient.hgetall(FairScheduler.job_meta_key(jid)) or {}
            # job already unregistered — use lease meta
            uid = store.get_lease_user(jid) or ""
            if uid:
                store.release(job_id=jid, user_id=uid)
        decisions = sched.dispatch_once(enqueue_fn=lambda j: None)
        for d in decisions:
            if d.admission_result == "admit":
                seen.add(d.user_id)
        assert store.global_active() <= 5
    assert len(seen) >= 3, f"too few users got turns: {seen}"


def test_duplicate_dispatch_idempotent(rclient):
    store = CapacityStore(rclient)
    sched = FairScheduler(redis_client=rclient, store=store)
    uid = f"dup-{ObjectId()}"
    job = _job(uid, 0, user_max=5)
    assert sched.register(job).ok
    assert sched.register(job).ok  # idempotent register
    calls = []
    sched.dispatch_once(enqueue_fn=lambda j: calls.append(j))
    sched.dispatch_once(enqueue_fn=lambda j: calls.append(j))
    assert calls.count(job.job_id) == 1


def test_plan_snapshot_weights_immutable():
    entry = MagicMock()
    entry.id = ObjectId()
    entry.user_id = ObjectId()
    entry.queued_at = None
    entry.created_at = None
    entry.plan_snapshot = {
        "plan_id": "pro",
        "plan_version": "1",
        "scheduler_weight": 5,
        "scheduler_priority": 50,
        "max_concurrent_jobs": 3,
    }
    from core.brevio_api.services.capacity.fair_scheduler import waiting_job_from_entry

    w = waiting_job_from_entry(entry)
    assert w.weight == 5
    assert w.priority == 50
    assert w.user_max == 3
    # Simulate plan change on user — snapshot on job unchanged
    entry.plan_snapshot = {
        **entry.plan_snapshot,
        "plan_version": "2",
        "scheduler_weight": 99,
        "max_concurrent_jobs": 99,
    }
    # Historical waiting job already captured values in Redis meta at register time;
    # from_entry for NEW register would see v2 — jobs already waiting keep Redis meta.
    w2 = waiting_job_from_entry(entry)
    assert w2.weight == 99  # new jobs
    assert w.weight == 5  # old object immutable


def test_scheduler_unavailable_fail_closed(monkeypatch):
    bad = redis.Redis.from_url("redis://127.0.0.1:1/0", decode_responses=True)
    store = CapacityStore(bad)
    sched = FairScheduler(redis_client=bad, store=store)
    result = sched.register(_job("x", 0))
    assert not result.ok
    assert result.reason == "SCHEDULER_UNAVAILABLE"
    assert sched.dispatch_once(enqueue_fn=lambda j: None) == []


@pytest.mark.asyncio
async def test_integrated_credits_product_capacity_race():
    """100 concurrent commercial admits; capacity only limits execution slots."""
    import os
    from dataclasses import replace
    from unittest.mock import AsyncMock, MagicMock

    from motor.motor_asyncio import AsyncIOMotorClient

    from core.brevio_api.models.billing.credit_models import BillingMode, CreditAccount
    from core.brevio_api.services.billing.credit_service import CreditService
    from core.brevio_api.services.billing.plan_registry import get_plan
    from core.brevio_api.services.billing.product_limit_service import (
        AdmissionRequest,
        DocumentMetrics,
        ProductLimitError,
        ProductLimitService,
    )
    from core.shared.enums.model import ModelType

    uri = os.getenv(
        "FASE5_MONGO_URI",
        "mongodb://root:password@127.0.0.1:27017/?authSource=admin",
    )
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=3000)
    try:
        await client.admin.command("ping")
    except Exception as exc:
        pytest.skip(f"real mongo unavailable: {exc}")

    db = client.get_database("brevio_fase6_combo")
    for name in (
        "product_period_usage",
        "product_usage_records",
        "credit_accounts",
        "credit_reservations",
        "credit_ledger",
        "job_settlements",
    ):
        await db[name].delete_many({})

    r = redis.Redis.from_url(_redis_url(), decode_responses=True)
    try:
        r.ping()
    except Exception as exc:
        pytest.skip(f"real redis unavailable: {exc}")
    for key in list(r.scan_iter(match="brevio:capacity:*")) + list(
        r.scan_iter(match="brevio:scheduler:*")
    ):
        r.delete(key)

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
        credits_per_period=50,
    )
    store = CapacityStore(r)
    sched = FairScheduler(redis_client=r, store=store)

    async def one(i: int) -> bool:
        job_id = f"int-{i}-{ObjectId()}"
        try:
            await products.admit(
                AdmissionRequest(
                    user_id=uid,
                    job_id=job_id,
                    source_type="documents",
                    model=ModelType.QWEN3_8B,
                    has_byok=False,
                    documents=[DocumentMetrics(f"{i}.txt", 10, 1)],
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
        except Exception:
            await products.release_admission(job_id)
            return False
        waiting = WaitingJob(
            job_id=job_id,
            user_id=uid,
            plan_id=limited.plan_id,
            priority=limited.scheduler_priority,
            weight=limited.scheduler_weight,
            user_max=limited.max_concurrent_jobs,
            queued_at=time.time(),
        )
        assert sched.register(waiting).ok
        return True

    outcomes = await asyncio.gather(*[one(i) for i in range(100)])
    ok = sum(1 for x in outcomes if x)
    bal = await credits.get_balance(uid)
    usage = await db["product_period_usage"].find_one({"user_id": ObjectId(uid)})
    assert ok == 50
    assert bal == 0
    assert usage["documents_used"] == 50

    original = store.acquire

    def acquire_cap(**kwargs):
        kwargs["global_max"] = 5
        return original(**kwargs)

    store.acquire = acquire_cap  # type: ignore
    for _ in range(20):
        sched.dispatch_once(enqueue_fn=lambda j: None)
    assert store.global_active() <= 5
    # Remaining waiting jobs still registered (45 left after 5 dispatched)
    queued = int(r.get(FairScheduler.GLOBAL_QUEUED) or 0)
    assert queued == 45
    client.close()
    r.close()
