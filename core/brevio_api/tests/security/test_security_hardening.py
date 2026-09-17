"""Security regression tests for upload hardening, SSRF, auth enumeration, and runtime guards."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from pydantic import HttpUrl, ValidationError

from core.brevio_api.__main__ import app
from core.brevio_api.dependencies.auth_service_dependency import get_auth_service
from core.brevio_api.dependencies.user_dependency import get_current_user
from core.brevio_api.models.auth.auth import LoginUser, RecoveryPassword, RegisterUser
from core.brevio_api.models.brevio.url_yt import UrlYT
from core.brevio_api.models.responses.auth_response import PasswordRecoveryResponse
from core.brevio_api.services.auth_service import AuthSession
from core.brevio_api.utils.otp_utils import OTPUtils
from core.brevio_api.utils.rate_limit import reset_rate_limiter_for_tests
from core.brevio_api.utils.security_runtime import assert_secure_runtime_config
from core.brevio_api.utils.upload_security import (
    ensure_path_inside,
    sanitize_upload_filename,
)
from core.shared.utils.youtube_url import normalize_youtube_url


@pytest.fixture(autouse=True)
def _reset_limits(monkeypatch: pytest.MonkeyPatch) -> Any:
    reset_rate_limiter_for_tests()
    monkeypatch.setenv("AUTH_RATE_LIMIT", "1000")
    yield
    reset_rate_limiter_for_tests()


def test_sanitize_upload_filename_blocks_traversal() -> None:
    assert sanitize_upload_filename("../../etc/passwd") == "passwd"
    assert sanitize_upload_filename("..\\..\\windows\\system32\\cmd.exe") == "cmd.exe"
    assert "/" not in sanitize_upload_filename("a/b/c.pdf")
    assert sanitize_upload_filename("../x.pdf") == "x.pdf"
    assert sanitize_upload_filename("") == "upload"
    assert sanitize_upload_filename("..") == "upload"


def test_ensure_path_inside_rejects_escape(tmp_path: Path) -> None:
    base = tmp_path / "data"
    base.mkdir()
    with pytest.raises(HTTPException) as exc:
        ensure_path_inside(base, base / ".." / "outside.txt")
    assert exc.value.status_code == 400


def test_youtube_url_rejects_ssrf_targets() -> None:
    with pytest.raises(ValueError):
        normalize_youtube_url("http://youtube.com/watch?v=x")
    with pytest.raises(ValueError):
        normalize_youtube_url("https://127.0.0.1/watch?v=x")
    with pytest.raises(ValueError):
        normalize_youtube_url("https://evil.com/youtube.com/watch?v=x")
    with pytest.raises(ValueError):
        normalize_youtube_url("https://youtube.com.evil.com/watch?v=x")
    with pytest.raises(ValueError):
        normalize_youtube_url("https://user:pass@youtube.com/watch?v=x")
    assert normalize_youtube_url(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    ).startswith("https://www.youtube.com/")


def test_url_yt_model_rejects_non_youtube() -> None:
    with pytest.raises(ValidationError):
        UrlYT(url=HttpUrl("https://example.com/watch?v=1"))
    with pytest.raises(ValidationError):
        UrlYT(url=HttpUrl("http://www.youtube.com/watch?v=1"))


def test_otp_uses_secure_generator_and_constant_time_compare() -> None:
    values = {OTPUtils.generate_otp() for _ in range(20)}
    assert len(values) > 1
    assert OTPUtils.constant_time_equals(123456, 123456)
    assert not OTPUtils.constant_time_equals(123456, 654321)


def test_production_runtime_rejects_weak_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("API_KEY", "local_api_key_123")
    monkeypatch.setenv("SECRET_TOKEN_KEY", "local_secret_key_123")
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", "")
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(RuntimeError):
        assert_secure_runtime_config()


def test_production_runtime_accepts_strong_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("API_KEY", "production-api-key-value-24chars-min")
    monkeypatch.setenv("SECRET_TOKEN_KEY", "production-jwt-secret-value-32chars-min!!")
    monkeypatch.setenv(
        "CREDENTIAL_ENCRYPTION_KEY",
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    )
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("TRUSTED_PROXY", "172.28.0.0/16")
    monkeypatch.setenv("REDIS_PASSWORD", "production-redis-pass-16+")
    assert_secure_runtime_config()


def test_production_runtime_requires_trusted_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("API_KEY", "production-api-key-value-24chars-min")
    monkeypatch.setenv("SECRET_TOKEN_KEY", "production-jwt-secret-value-32chars-min!!")
    monkeypatch.setenv(
        "CREDENTIAL_ENCRYPTION_KEY",
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    )
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("REDIS_PASSWORD", "production-redis-pass-16+")
    monkeypatch.delenv("TRUSTED_PROXY", raising=False)
    with pytest.raises(RuntimeError, match="TRUSTED_PROXY"):
        assert_secure_runtime_config()


def test_production_runtime_requires_redis_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("API_KEY", "production-api-key-value-24chars-min")
    monkeypatch.setenv("SECRET_TOKEN_KEY", "production-jwt-secret-value-32chars-min!!")
    monkeypatch.setenv(
        "CREDENTIAL_ENCRYPTION_KEY",
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    )
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("TRUSTED_PROXY", "172.28.0.0/16")
    monkeypatch.delenv("REDIS_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="REDIS_PASSWORD"):
        assert_secure_runtime_config()


def test_production_rejects_open_trusted_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("API_KEY", "production-api-key-value-24chars-min")
    monkeypatch.setenv("SECRET_TOKEN_KEY", "production-jwt-secret-value-32chars-min!!")
    monkeypatch.setenv(
        "CREDENTIAL_ENCRYPTION_KEY",
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    )
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("REDIS_PASSWORD", "production-redis-pass-16+")
    monkeypatch.setenv("TRUSTED_PROXY", "0.0.0.0/0")
    with pytest.raises(RuntimeError, match="TRUSTED_PROXY"):
        assert_secure_runtime_config()


class _EnumAuthService:
    async def login(self, login_user: LoginUser) -> AuthSession:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    async def register(self, register_user: RegisterUser) -> AuthSession:
        raise HTTPException(
            status_code=400,
            detail="Unable to register with the provided credentials",
        )

    async def password_recovery_handshake(
        self, recovery_password: RecoveryPassword
    ) -> PasswordRecoveryResponse:
        return PasswordRecoveryResponse(
            message="Si la cuenta existe, se ha enviado un código de recuperación."
        )


def test_auth_rate_limit_triggers_429(monkeypatch: pytest.MonkeyPatch) -> None:
    import redis

    redis_url = os.getenv("FASE7_REDIS_URI", "redis://127.0.0.1:6380/14")
    try:
        redis.Redis.from_url(redis_url, decode_responses=True).ping()
    except Exception as exc:
        pytest.skip(f"real redis unavailable: {exc}")

    monkeypatch.setenv("ANTI_ABUSE_REDIS_URL", redis_url)
    monkeypatch.setenv("AUTH_RATE_LIMIT", "3")
    monkeypatch.setenv("AUTH_RATE_WINDOW_SECONDS", "60")
    monkeypatch.setenv("IP_GLOBAL_RATE_LIMIT", "1000")
    monkeypatch.setenv("ANTI_ABUSE_ENABLED", "0")
    reset_rate_limiter_for_tests()
    app.dependency_overrides[get_auth_service] = lambda: _EnumAuthService()
    client = TestClient(app)
    try:
        payload = {"identity": "user123", "password": "Aa1@aaa!"}
        codes = [
            client.post("/auth/login", json=payload).status_code for _ in range(4)
        ]
        assert 429 in codes
    finally:
        app.dependency_overrides.clear()
        reset_rate_limiter_for_tests()


def test_yt_count_requires_user_auth_not_only_api_key() -> None:
    client = TestClient(app)
    response = client.post(
        "/brevio/count-yt-videos",
        json={"url": "https://www.youtube.com/playlist?list=ABC"},
        headers={"X-API-KEY": "local_api_key_123"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_yt_count_with_user_auth_reaches_service(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.brevio_api.dependencies.brevio_service_dependency import get_brevio_service

    service = AsyncMock()
    service.count_media_in_yt_playlist = AsyncMock(return_value=3)
    app.dependency_overrides[get_current_user] = lambda: "507f1f77bcf86cd799439011"
    app.dependency_overrides[get_brevio_service] = lambda: service
    client = TestClient(app)
    try:
        response = client.post(
            "/brevio/count-yt-videos",
            json={"url": "https://www.youtube.com/playlist?list=ABC"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 3
    finally:
        app.dependency_overrides.clear()


def test_security_headers_present() -> None:
    client = TestClient(app)
    response = client.get("/__security_probe_missing__")
    assert response.status_code == 404
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
