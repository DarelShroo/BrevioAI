from __future__ import annotations

import re

_SECRET_RE = re.compile(
    r"(?i)(sk-[A-Za-z0-9_-]{8,}|Bearer\s+\S+|api[_-]?key['\"]?\s*[:=]\s*['\"][^'\"]+['\"])"
)


def redact_secrets(value: str | None) -> str:
    if not value:
        return ""
    return _SECRET_RE.sub("[REDACTED]", value)
