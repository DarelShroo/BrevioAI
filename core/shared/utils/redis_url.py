"""Redis URL credential injection (no secrets in code).

When ``REDIS_PASSWORD`` (and optional ``REDIS_USERNAME``) are set, any Redis URL
that lacks userinfo gets credentials injected. URLs that already embed
credentials are left unchanged.

Production compose uses Redis ACL user ``brevio`` (see ``deploy/redis/``).
Development may omit ``REDIS_PASSWORD`` and keep open Redis on the Docker network.
"""

from __future__ import annotations

import os
from urllib.parse import quote, urlparse, urlunparse


DEFAULT_REDIS_USERNAME = "brevio"


def redis_username() -> str:
    return (os.getenv("REDIS_USERNAME") or DEFAULT_REDIS_USERNAME).strip() or DEFAULT_REDIS_USERNAME


def redis_password() -> str:
    return os.getenv("REDIS_PASSWORD", "").strip()


def resolve_redis_url(url: str | None) -> str:
    """Return ``url`` with ACL credentials applied when configured."""
    raw = (url or "").strip()
    if not raw:
        return raw
    password = redis_password()
    if not password:
        return raw
    parsed = urlparse(raw)
    if parsed.scheme not in {"redis", "rediss"}:
        return raw
    # Already has userinfo — do not override explicit credentials.
    if parsed.password is not None or parsed.username:
        return raw
    user = redis_username()
    netloc = f"{quote(user, safe='')}:{quote(password, safe='')}@{parsed.hostname or 'localhost'}"
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return urlunparse(
        (
            parsed.scheme,
            netloc,
            parsed.path or "",
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )
