"""Redis key builders. Never embed API keys."""

from __future__ import annotations


def build_quota_scope_id(
    *, is_platform: bool, credential_id: str, policy_scope: str | None = None
) -> str:
    """
    Prefer admin policy_scope (e.g. gcp-project:X) when provided.
    Fallback: platform | cred:{credential_id}.

    Two API keys for the same Google project share Google quota; map both to
    gcp-project:X in YAML when the project id is known.
    """
    if policy_scope:
        return policy_scope
    if is_platform:
        return "platform"
    return f"cred:{credential_id}"


def redis_prefix(
    provider: str,
    quota_scope_id: str,
    model: str,
    quota_group: str | None = None,
) -> str:
    # Sanitize separators. quota_group lets models that share a provider quota
    # (same RPM bucket) share Redis keys without inventing per-vendor defaults.
    safe_scope = quota_scope_id.replace(" ", "_")
    bucket = (quota_group or model).replace(" ", "_")
    return f"brevio:pq:{provider.lower()}:{safe_scope}:{bucket}"


def inflight_key(prefix: str) -> str:
    return f"{prefix}:inflight"


def rpm_key(prefix: str) -> str:
    return f"{prefix}:rpm"


def tpm_key(prefix: str) -> str:
    return f"{prefix}:tpm"


def cooldown_key(prefix: str) -> str:
    return f"{prefix}:cooldown"


def degraded_key(prefix: str) -> str:
    """Half-open circuit after 429: serialize inflight until a success."""
    return f"{prefix}:degraded"
