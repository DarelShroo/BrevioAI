"""Redis URL credential injection + production Redis ACL guards."""

from __future__ import annotations

import os

import pytest

from core.shared.utils.redis_url import resolve_redis_url


def test_resolve_redis_url_noop_without_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REDIS_PASSWORD", raising=False)
    assert (
        resolve_redis_url("redis://redis:6379/0") == "redis://redis:6379/0"
    )


def test_resolve_redis_url_injects_acl_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_PASSWORD", "s3cret-pass-value")
    monkeypatch.setenv("REDIS_USERNAME", "brevio")
    assert resolve_redis_url("redis://redis:6379/2") == (
        "redis://brevio:s3cret-pass-value@redis:6379/2"
    )


def test_resolve_redis_url_preserves_explicit_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REDIS_PASSWORD", "env-password-should-not-override")
    assert resolve_redis_url("redis://other:explicit@redis:6379/0") == (
        "redis://other:explicit@redis:6379/0"
    )


def test_resolve_redis_url_quotes_special_chars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_PASSWORD", "p@ss/word:x")
    monkeypatch.setenv("REDIS_USERNAME", "brevio")
    out = resolve_redis_url("redis://127.0.0.1:6379/0")
    assert out.startswith("redis://brevio:")
    assert "@127.0.0.1:6379/0" in out
    assert "p%40ss%2Fword%3Ax" in out


@pytest.mark.integration
def test_redis_acl_auth_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Optional: validates ACL against a password-protected Redis if configured."""
    import redis

    url = os.getenv("P0_REDIS_ACL_URL", "").strip()
    if not url:
        pytest.skip("Set P0_REDIS_ACL_URL to exercise live Redis ACL")
    client = redis.Redis.from_url(url, decode_responses=True)
    assert client.ping() is True
    # Unauthenticated peer must fail when ACL is enforced.
    bare = os.getenv("P0_REDIS_ACL_BARE_URL", "").strip()
    if bare:
        bad = redis.Redis.from_url(bare, decode_responses=True, socket_connect_timeout=2)
        with pytest.raises(Exception):
            bad.ping()
