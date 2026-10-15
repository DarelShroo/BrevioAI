"""FASE 7: distributed rate limiting + anti-abuse (Redis real)."""

from __future__ import annotations

import asyncio
import os
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
import redis
from fastapi import Request
from starlette.datastructures import Headers

from core.brevio_api.models.errors.api_codes import ApiErrorCode, CodedHTTPException
from core.brevio_api.services.anti_abuse.abuse_guard import AbuseGuard
from core.brevio_api.services.anti_abuse.config import (
    BucketConfig,
    abuse_cooldown_seconds,
    abuse_violation_threshold,
)
from core.brevio_api.services.anti_abuse.enforce import (
    client_ip,
    enforce_auth_rate_limit,
    reset_rate_limiter_for_tests,
)
from core.brevio_api.services.anti_abuse.rate_limiter import DistributedRateLimiter
from core.brevio_api.services.capacity.fair_scheduler import FairScheduler, WaitingJob


def _redis_url() -> str:
    return os.getenv(
        "FASE7_REDIS_URI",
        os.getenv(
            "ANTI_ABUSE_REDIS_URL",
            os.getenv("CAPACITY_REDIS_URL", "redis://127.0.0.1:6380/14"),
        ),
    )


@pytest.fixture
def rclient():
    client = redis.Redis.from_url(_redis_url(), decode_responses=True)
    try:
        client.ping()
    except Exception as exc:
        pytest.skip(f"real redis unavailable: {exc}")
    for key in list(client.scan_iter(match="antiabuse:*")):
        client.delete(key)
    for key in list(client.scan_iter(match="brevio:scheduler:*")):
        client.delete(key)
    yield client
    for key in list(client.scan_iter(match="antiabuse:*")):
        client.delete(key)
    client.close()
    reset_rate_limiter_for_tests()


def test_rate_limit_50_of_100(rclient, monkeypatch):
    monkeypatch.setenv("ANTI_ABUSE_REDIS_URL", _redis_url())
    reset_rate_limiter_for_tests()
    limiter = DistributedRateLimiter(rclient)
    bucket = BucketConfig("t50", 50, 60, fail_closed=True)
    ok = sum(
        1
        for i in range(100)
        if limiter.hit(identity=f"user:u1", bucket=bucket).allowed
    )
    assert ok == 50


def test_concurrent_same_user(rclient):
    limiter = DistributedRateLimiter(rclient)
    bucket = BucketConfig("conc", 50, 60, fail_closed=True)

    def one(_):
        return limiter.hit(identity="user:conc", bucket=bucket).allowed

    with ThreadPoolExecutor(max_workers=32) as pool:
        outcomes = list(pool.map(one, range(100)))
    assert sum(1 for x in outcomes if x) == 50


def test_multi_process_shared_redis(rclient):
    """Simulate two replicas sharing Redis (two limiter instances)."""
    a = DistributedRateLimiter(rclient)
    b = DistributedRateLimiter(rclient)
    bucket = BucketConfig("replica", 50, 60, fail_closed=True)
    ok = 0
    for i in range(100):
        lim = a if i % 2 == 0 else b
        if lim.hit(identity="user:replica", bucket=bucket).allowed:
            ok += 1
    assert ok == 50


def test_ttl_window_expires(rclient):
    limiter = DistributedRateLimiter(rclient)
    bucket = BucketConfig("ttl", 2, 1, fail_closed=True)
    assert limiter.hit(identity="user:ttl", bucket=bucket).allowed
    assert limiter.hit(identity="user:ttl", bucket=bucket).allowed
    denied = limiter.hit(identity="user:ttl", bucket=bucket)
    assert not denied.allowed
    time.sleep(1.2)
    assert limiter.hit(identity="user:ttl", bucket=bucket).allowed


def test_redis_fail_closed_expensive(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    bad = redis.Redis.from_url("redis://127.0.0.1:1/0", decode_responses=True)
    limiter = DistributedRateLimiter(bad)
    bucket = BucketConfig("fail", 10, 60, fail_closed=True)
    result = limiter.hit(identity="user:x", bucket=bucket)
    assert not result.allowed


def test_redis_fail_open_cheap(monkeypatch):
    bad = redis.Redis.from_url("redis://127.0.0.1:1/0", decode_responses=True)
    limiter = DistributedRateLimiter(bad)
    bucket = BucketConfig("cheap", 10, 60, fail_closed=False)
    result = limiter.hit(identity="user:y", bucket=bucket)
    assert result.allowed


def test_trusted_proxy_ip(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY", "127.0.0.1/32")
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": Headers(
            {"x-forwarded-for": "203.0.113.9, 10.0.0.1"}
        ).raw,
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
    }
    req = Request(scope)
    assert client_ip(req) == "203.0.113.9"


def test_untrusted_xff_ignored(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY", "10.0.0.0/8")
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": Headers({"x-forwarded-for": "203.0.113.9"}).raw,
        "client": ("198.51.100.1", 12345),
        "server": ("test", 80),
    }
    req = Request(scope)
    assert client_ip(req) == "198.51.100.1"


def test_abuse_cooldown(rclient, monkeypatch):
    monkeypatch.setenv("ANTI_ABUSE_VIOLATION_THRESHOLD", "3")
    monkeypatch.setenv("ANTI_ABUSE_COOLDOWN_SECONDS", "2")
    monkeypatch.setenv("ANTI_ABUSE_VIOLATION_TTL_SECONDS", "60")
    guard = AbuseGuard(rclient)
    subject = f"user:{uuid4().hex}"
    assert not guard.check_cooldown(subject).active
    guard.record_violation(subject)
    guard.record_violation(subject)
    status = guard.record_violation(subject)
    assert status.active
    assert guard.check_cooldown(subject).active
    time.sleep(2.2)
    assert not guard.check_cooldown(subject).active


def test_global_queued_atomic_register(rclient, monkeypatch):
    monkeypatch.setenv("GLOBAL_MAX_QUEUED_JOBS", "50")
    monkeypatch.setenv("CAPACITY_MAX_QUEUED_JOBS_PER_USER", "200")
    from core.brevio_api.services.capacity import CapacityStore

    store = CapacityStore(rclient)
    sched = FairScheduler(redis_client=rclient, store=store)

    def one(i: int) -> bool:
        job = WaitingJob(
            job_id=f"q-{i}-{uuid4().hex}",
            user_id=f"u-{i % 10}",
            plan_id="pro",
            priority=10,
            weight=1,
            user_max=10,
            queued_at=time.time(),
        )
        return sched.register(job).ok

    with ThreadPoolExecutor(max_workers=32) as pool:
        outcomes = list(pool.map(one, range(100)))
    assert sum(1 for x in outcomes if x) == 50
    assert int(rclient.get(FairScheduler.GLOBAL_QUEUED) or 0) == 50


def test_ip_and_user_dimensions(rclient):
    limiter = DistributedRateLimiter(rclient)
    bucket = BucketConfig("dim", 5, 60, fail_closed=True)
    # Same IP different users share IP bucket when identity is ip:...
    for i in range(5):
        assert limiter.hit(identity="ip:1.1.1.1", bucket=bucket).allowed
    assert not limiter.hit(identity="ip:1.1.1.1", bucket=bucket).allowed
    # User buckets independent
    assert limiter.hit(identity="user:a", bucket=bucket).allowed
    assert limiter.hit(identity="user:b", bucket=bucket).allowed


def _auth_request(ip: str = "203.0.113.50") -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/auth/refresh",
        "raw_path": b"/auth/refresh",
        "query_string": b"",
        "headers": Headers({}).raw,
        "client": (ip, 12345),
        "server": ("test", 80),
    }
    return Request(scope)


def test_refresh_rate_limit_does_not_feed_abuse_cooldown(rclient, monkeypatch):
    monkeypatch.setenv("ANTI_ABUSE_REDIS_URL", _redis_url())
    monkeypatch.setenv("AUTH_REFRESH_RATE_LIMIT", "2")
    monkeypatch.setenv("AUTH_REFRESH_RATE_WINDOW_SECONDS", "60")
    monkeypatch.setenv("IP_GLOBAL_RATE_LIMIT", "1000")
    monkeypatch.setenv("ANTI_ABUSE_VIOLATION_THRESHOLD", "2")
    monkeypatch.setenv("ANTI_ABUSE_COOLDOWN_SECONDS", "60")
    monkeypatch.setenv("TRUSTED_PROXY", "")
    reset_rate_limiter_for_tests()

    req = _auth_request()
    enforce_auth_rate_limit(req, "refresh")
    enforce_auth_rate_limit(req, "refresh")
    with pytest.raises(CodedHTTPException) as exc:
        enforce_auth_rate_limit(req, "refresh")
    assert exc.value.status_code == 429
    assert exc.value.code == ApiErrorCode.RATE_LIMITED

    # Exhausted refresh must not open an abuse cooldown (login must still work).
    guard = AbuseGuard(rclient)
    assert not guard.check_cooldown("ip:203.0.113.50").active
    assert rclient.get("antiabuse:violations:ip:203.0.113.50") in (None, "0")
