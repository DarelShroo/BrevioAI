from datetime import timedelta

from fastapi import HTTPException
from starlette.responses import Response

from core.brevio_api.services.auth_cookies import (
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    clear_auth_cookies,
    set_auth_cookies,
)
from core.brevio_api.services.token_service import (
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    TokenService,
)


def test_access_token_uses_configured_ttl(monkeypatch) -> None:
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    service = TokenService()
    assert service.access_max_age_seconds == 15 * 60
    token = service.create_access_token({"id": "507f1f77bcf86cd799439011"})
    payload = service.validate_access_token(token)
    assert payload["id"] == "507f1f77bcf86cd799439011"
    assert payload["typ"] == TOKEN_TYPE_ACCESS


def test_refresh_token_cannot_be_used_as_access() -> None:
    service = TokenService()
    token, jti = service.create_refresh_token("user-1", "family-1")
    assert jti
    payload = service.validate_refresh_token(token)
    assert payload["typ"] == TOKEN_TYPE_REFRESH
    try:
        service.validate_access_token(token)
        assert False, "refresh token must not validate as access"
    except HTTPException as exc:
        assert exc.status_code == 401


def test_expired_access_token_is_rejected() -> None:
    service = TokenService()
    token = service.create_access_token(
        {"id": "user-1"}, expires_delta=timedelta(seconds=-2)
    )
    try:
        service.validate_access_token(token)
        assert False, "expired token must be rejected"
    except HTTPException as exc:
        assert exc.status_code == 401


def test_auth_cookies_are_httponly_host_only_and_strict() -> None:
    response = Response()
    set_auth_cookies(
        response,
        access_token="access",
        refresh_token="refresh",
        access_max_age=900,
        refresh_max_age=604800,
    )
    headers = response.headers.getlist("set-cookie")
    access = next(item for item in headers if item.startswith(f"{ACCESS_COOKIE_NAME}="))
    refresh = next(
        item for item in headers if item.startswith(f"{REFRESH_COOKIE_NAME}=")
    )
    assert "HttpOnly" in access
    assert "HttpOnly" in refresh
    assert "samesite=strict" in access.lower()
    assert "samesite=strict" in refresh.lower()
    assert "domain=" not in access.lower()
    assert "path=/auth" in refresh.lower()
    clear_auth_cookies(response)
    cleared = response.headers.getlist("set-cookie")
    assert any("max-age=0" in item.lower() for item in cleared)
