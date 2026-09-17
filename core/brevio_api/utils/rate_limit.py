"""Backward-compatible auth rate-limit API (FASE 7 → Redis distributed).

Previously in-process sliding window (per worker). Now delegates to
``services.anti_abuse`` Redis fixed-window limiter.
"""

from __future__ import annotations

from fastapi import Request

from core.brevio_api.services.anti_abuse.enforce import (
    client_ip,
    enforce_auth_rate_limit,
    reset_rate_limiter_for_tests,
)

__all__ = [
    "client_ip",
    "enforce_auth_rate_limit",
    "reset_rate_limiter_for_tests",
]


# Re-export for existing imports: ``from core.brevio_api.utils.rate_limit import ...``
def _compat_enforce(request: Request, action: str) -> None:
    enforce_auth_rate_limit(request, action)
