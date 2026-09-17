"""Production startup guards and security-related FastAPI helpers."""

from __future__ import annotations

import logging
import os
import secrets
from typing import Optional

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.shared.utils.environment import is_production_environment, jwt_secret_key

logger = logging.getLogger(__name__)

_WEAK_API_KEYS = frozenset(
    {
        "",
        "DEFAULT_SECRET_KEY",
        "local_api_key_123",
        "changeme",
        "secret",
        "api_key",
    }
)
_WEAK_JWT_SECRETS = frozenset(
    {
        "",
        "default_secret_key",
        "local_secret_key_123",
        "changeme",
        "secret",
    }
)


def assert_secure_runtime_config() -> None:
    """Fail closed when production would boot with insecure defaults."""
    if not is_production_environment():
        return

    api_key = os.getenv("API_KEY", "")
    if api_key.strip() in _WEAK_API_KEYS or len(api_key.strip()) < 24:
        raise RuntimeError(
            "Refusing to start: set a strong API_KEY (min 24 chars) in production"
        )

    secret = jwt_secret_key()
    if secret.strip() in _WEAK_JWT_SECRETS or len(secret.strip()) < 32:
        raise RuntimeError(
            "Refusing to start: set a strong SECRET_TOKEN_KEY (min 32 chars) in production"
        )

    if not os.getenv("CREDENTIAL_ENCRYPTION_KEY", "").strip():
        raise RuntimeError(
            "Refusing to start: CREDENTIAL_ENCRYPTION_KEY is required in production"
        )

    cors = os.getenv("CORS_ORIGINS", "")
    if not cors.strip() or "*" in cors:
        raise RuntimeError(
            "Refusing to start: CORS_ORIGINS must be an explicit allow-list in production"
        )

    # Production must pin TRUSTED_PROXY to the real ingress CIDR, not all RFC1918.
    trusted = os.getenv("TRUSTED_PROXY", "").strip()
    if not trusted:
        raise RuntimeError(
            "Refusing to start: set TRUSTED_PROXY to your ingress/nginx CIDR in production"
        )
    if trusted == "*":
        raise RuntimeError(
            "Refusing to start: TRUSTED_PROXY=* is not allowed in production"
        )
    insecure_proxy = {
        "0.0.0.0/0",
        "::/0",
        "0.0.0.0",
        "::",
    }
    for part in (p.strip() for p in trusted.split(",") if p.strip()):
        if part in insecure_proxy:
            raise RuntimeError(
                f"Refusing to start: TRUSTED_PROXY value {part!r} trusts the entire internet"
            )

    # Redis ACL password required for production (injected into Redis URLs).
    if not os.getenv("REDIS_PASSWORD", "").strip():
        raise RuntimeError(
            "Refusing to start: REDIS_PASSWORD is required in production "
            "(Redis ACL user; see deploy/redis/entrypoint.sh)"
        )
    if len(os.getenv("REDIS_PASSWORD", "").strip()) < 16:
        raise RuntimeError(
            "Refusing to start: REDIS_PASSWORD must be at least 16 characters in production"
        )


def docs_urls_for_environment() -> tuple[Optional[str], Optional[str], Optional[str]]:
    if is_production_environment() and os.getenv("EXPOSE_API_DOCS", "").lower() not in {
        "1",
        "true",
        "yes",
    }:
        return None, None, None
    return "/api/docs", "/api/redoc", "/api/openapi.json"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        # Public example PDFs must be embeddable in the frontend compare demo.
        path = request.url.path or ""
        if not (path.startswith("/examples/") and path.endswith("/pdf")):
            response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=()",
        )
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        if is_production_environment():
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


def constant_time_equals(left: str, right: str) -> bool:
    return secrets.compare_digest(left.encode("utf-8"), right.encode("utf-8"))
