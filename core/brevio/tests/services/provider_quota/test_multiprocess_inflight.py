"""
FASE 3/8 mandatory: 4 processes × 8 coroutines = 32 attempts, max_in_flight=3.
Also SIGKILL lease reclaim.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from multiprocessing import Process, Queue

import pytest

pytestmark = pytest.mark.redis

REDIS_URL = os.getenv("PROVIDER_QUOTA_TEST_REDIS_URL", "redis://127.0.0.1:6379/14")


def _worker_run(
    result_q: Queue, n_coroutines: int, max_in_flight: int, prefix: str, hold_ms: int
):
    import asyncio

    import redis.asyncio as redis_async

    from core.brevio.services.provider_quota.redis_store import RedisQuotaStore

    async def one(store, idx):
        # Simulate HTTP gate using Redis counter while holding lease
        r = await store.acquire(
            prefix=prefix,
            max_in_flight=max_in_flight,
            lease_ttl_ms=10_000,
            rpm_limit=None,
            tpm_limit=None,
            reserved_input_tokens=0,
            lease_id=f"{os.getpid()}-{idx}-{uuid.uuid4()}",
        )
        if not r.ok:
            # spin until granted (short)
            for _ in range(200):
                await asyncio.sleep(0.02)
                r = await store.acquire(
                    prefix=prefix,
                    max_in_flight=max_in_flight,
                    lease_ttl_ms=10_000,
                    rpm_limit=None,
                    tpm_limit=None,
                    reserved_input_tokens=0,
                    lease_id=f"{os.getpid()}-{idx}-{uuid.uuid4()}",
                )
                if r.ok:
                    break
            if not r.ok:
                result_q.put(("denied", os.getpid(), 0))
                return

        client = store._r
        cur = await client.incr(f"{prefix}:http_inflight")
        peak = await client.get(f"{prefix}:http_peak")
        peak_i = int(peak or 0)
        if cur > peak_i:
            await client.set(f"{prefix}:http_peak", cur)
        await asyncio.sleep(hold_ms / 1000.0)
        await client.decr(f"{prefix}:http_inflight")
        await store.release(
            prefix=prefix,
            lease_id=r.lease_id,
            reserved_input_tokens=0,
            actual_prompt_tokens=None,
            tpm_limit=None,
            allow_refund=False,
        )
        result_q.put(("ok", os.getpid(), cur))

    async def main():
        client = redis_async.from_url(REDIS_URL, decode_responses=False)
        store = RedisQuotaStore(client)
        await asyncio.gather(*[one(store, i) for i in range(n_coroutines)])
        await client.aclose()

    asyncio.run(main())


def test_multiprocess_max_in_flight_global():
    import redis

    try:
        sync = redis.Redis.from_url(REDIS_URL)
        sync.ping()
    except Exception as e:
        pytest.skip(f"Redis required: {e}")

    prefix = f"brevio:pq:test:mp:{uuid.uuid4()}"
    sync = redis.Redis.from_url(REDIS_URL)
    # clear related keys via prefix pattern not needed; use unique prefix
    sync.delete(f"{prefix}:http_inflight", f"{prefix}:http_peak")

    q: Queue = Queue()
    procs = [Process(target=_worker_run, args=(q, 8, 3, prefix, 80)) for _ in range(4)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=60)
        assert p.exitcode == 0, f"worker exit {p.exitcode}"

    results = []
    while not q.empty():
        results.append(q.get())
    assert len(results) == 32
    peak = int(sync.get(f"{prefix}:http_peak") or 0)
    assert peak <= 3, f"max_observed_http_in_flight={peak} > 3"
    assert peak >= 1
    final = int(sync.get(f"{prefix}:http_inflight") or 0)
    assert final == 0


def _zombie_holder(prefix: str, lease_ttl_ms: int):
    import asyncio

    import redis.asyncio as redis_async

    from core.brevio.services.provider_quota.redis_store import RedisQuotaStore

    async def main():
        client = redis_async.from_url(REDIS_URL, decode_responses=False)
        store = RedisQuotaStore(client)
        r = await store.acquire(
            prefix=prefix,
            max_in_flight=1,
            lease_ttl_ms=lease_ttl_ms,
            rpm_limit=None,
            tpm_limit=None,
            reserved_input_tokens=0,
        )
        assert r.ok
        # Hold without release until killed
        await asyncio.sleep(60)
        await client.aclose()

    asyncio.run(main())


def test_sigkill_lease_reclaimed_by_ttl():
    import signal

    import redis

    try:
        sync = redis.Redis.from_url(REDIS_URL)
        sync.ping()
    except Exception as e:
        pytest.skip(f"Redis required: {e}")

    prefix = f"brevio:pq:test:kill:{uuid.uuid4()}"
    p = Process(target=_zombie_holder, args=(prefix, 800))
    p.start()
    time.sleep(0.3)
    os.kill(p.pid, signal.SIGKILL)
    p.join(timeout=5)

    import asyncio

    import redis.asyncio as redis_async

    from core.brevio.services.provider_quota.redis_store import RedisQuotaStore

    async def reclaim():
        client = redis_async.from_url(REDIS_URL, decode_responses=False)
        store = RedisQuotaStore(client)
        await asyncio.sleep(1.0)
        r = await store.acquire(
            prefix=prefix,
            max_in_flight=1,
            lease_ttl_ms=2000,
            rpm_limit=None,
            tpm_limit=None,
            reserved_input_tokens=0,
        )
        await client.aclose()
        return r

    r = asyncio.run(reclaim())
    assert r.ok, f"lease not reclaimed: {r.reason}"
