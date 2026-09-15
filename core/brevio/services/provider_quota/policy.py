"""Admin-owned quota policies. No invented Google defaults in code."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

from core.brevio.services.provider_quota.errors import QuotaPolicyMissingError
from core.shared.utils.environment import (
    map_original_text_fallback_override,
    provider_quota_is_enabled,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QuotaPolicy:
    provider: str
    model: str
    max_in_flight: int
    lease_ttl_ms: int
    acquire_timeout_ms: int
    max_attempts: int
    backoff_base_seconds: float
    backoff_max_seconds: float
    jitter_ratio: float
    rpm: Optional[int] = None  # requests_per_minute alias in YAML
    tpm: Optional[int] = None  # input tokens per minute (Google semantics)
    cooldown_on_429_seconds: Optional[float] = None
    quota_scope: Optional[str] = None  # e.g. gcp-project:X
    quota_group: Optional[str] = None  # shared Redis bucket across models
    rate_limit_safety_margin: float = 0.0
    job_max_provider_requests: Optional[int] = None
    degraded_max_in_flight: int = 1
    allow_map_original_text_fallback: bool = False


# Used only when PROVIDER_QUOTA_ENABLED=false for retry behavior alone.
DEFAULT_RETRY_ONLY_POLICY = QuotaPolicy(
    provider="*",
    model="*",
    max_in_flight=10**9,
    lease_ttl_ms=300_000,
    acquire_timeout_ms=300_000,
    max_attempts=5,
    backoff_base_seconds=1.0,
    backoff_max_seconds=60.0,
    jitter_ratio=0.25,
    rpm=None,
    tpm=None,
    cooldown_on_429_seconds=None,
    quota_scope=None,
    quota_group=None,
    rate_limit_safety_margin=0.0,
    job_max_provider_requests=None,
    degraded_max_in_flight=1,
    allow_map_original_text_fallback=False,
)


def _optional_int(entry: dict[str, Any], *keys: str) -> Optional[int]:
    for key in keys:
        if entry.get(key) is not None:
            return int(entry[key])
    return None


def _optional_float(entry: dict[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        if entry.get(key) is not None:
            return float(entry[key])
    return None


def effective_rpm(policy: QuotaPolicy) -> Optional[int]:
    """Apply rate_limit_safety_margin to the configured RPM. None means unlimited."""
    if policy.rpm is None or policy.rpm <= 0:
        return None
    margin = min(max(policy.rate_limit_safety_margin, 0.0), 0.9)
    return max(1, int(policy.rpm * (1.0 - margin)))


def _parse_policy_entry(entry: dict[str, Any]) -> QuotaPolicy:
    max_in_flight = entry.get("max_in_flight", entry.get("max_in_flight_requests"))
    required = ["provider", "model", "lease_ttl_ms"]
    missing = [k for k in required if k not in entry]
    if max_in_flight is None:
        missing.append("max_in_flight")
    if missing:
        raise QuotaPolicyMissingError(f"Quota policy entry missing fields: {missing}")
    retry_max = entry.get("max_attempts", entry.get("retry_max_attempts", 5))
    return QuotaPolicy(
        provider=str(entry["provider"]).lower(),
        model=str(entry["model"]),
        max_in_flight=int(max_in_flight),
        lease_ttl_ms=int(entry["lease_ttl_ms"]),
        acquire_timeout_ms=int(entry.get("acquire_timeout_ms", 300_000)),
        max_attempts=int(retry_max),
        backoff_base_seconds=float(
            entry.get("backoff_base_seconds", entry.get("retry_backoff", 1.0))
        ),
        backoff_max_seconds=float(entry.get("backoff_max_seconds", 60.0)),
        jitter_ratio=float(entry.get("jitter_ratio", 0.25)),
        rpm=_optional_int(entry, "rpm", "requests_per_minute"),
        tpm=_optional_int(entry, "tpm"),
        cooldown_on_429_seconds=_optional_float(entry, "cooldown_on_429_seconds"),
        quota_scope=str(entry["quota_scope"]) if entry.get("quota_scope") else None,
        quota_group=str(entry["quota_group"]) if entry.get("quota_group") else None,
        rate_limit_safety_margin=float(entry.get("rate_limit_safety_margin", 0.0)),
        job_max_provider_requests=_optional_int(entry, "job_max_provider_requests"),
        degraded_max_in_flight=int(entry.get("degraded_max_in_flight", 1)),
        allow_map_original_text_fallback=bool(
            entry.get("allow_map_original_text_fallback", False)
        ),
    )


def load_quota_policies(path: Optional[str] = None) -> list[QuotaPolicy]:
    config_path = path or os.getenv("PROVIDER_QUOTA_CONFIG_PATH")
    if not config_path:
        return []
    p = Path(config_path)
    if not p.is_file():
        raise QuotaPolicyMissingError(
            f"PROVIDER_QUOTA_CONFIG_PATH not found: {config_path}"
        )
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    entries = raw.get("policies") or []
    policies = [_parse_policy_entry(e) for e in entries]
    for policy in policies:
        if policy.rpm is None:
            logger.warning(
                "Quota policy provider=%s model=%s has no requests_per_minute; "
                "RPM is unlimited and only max_in_flight/cooldown apply. "
                "Set requests_per_minute from the provider console.",
                policy.provider,
                policy.model,
            )
    return policies


class QuotaPolicyRegistry:
    def __init__(self, policies: Optional[list[QuotaPolicy]] = None):
        self._policies = policies if policies is not None else []

    @classmethod
    def from_env(cls) -> "QuotaPolicyRegistry":
        try:
            return cls(load_quota_policies())
        except QuotaPolicyMissingError:
            raise
        except Exception as e:
            raise QuotaPolicyMissingError(f"Failed to load quota policies: {e}") from e

    def resolve(
        self,
        provider: str,
        model: str,
        *,
        require: bool,
        quota_scope_id: Optional[str] = None,
    ) -> QuotaPolicy:
        provider_l = provider.lower()
        # Prefer exact scope match, then provider+model, then provider+*
        candidates = [
            p
            for p in self._policies
            if p.provider == provider_l and (p.model == model or p.model == "*")
        ]
        if quota_scope_id:
            scoped = [p for p in candidates if p.quota_scope == quota_scope_id]
            if scoped:
                candidates = scoped
        if not candidates:
            if require:
                raise QuotaPolicyMissingError(
                    f"No quota policy for provider={provider} model={model}. "
                    "Configure PROVIDER_QUOTA_CONFIG_PATH (fail-closed)."
                )
            return DEFAULT_RETRY_ONLY_POLICY
        # Prefer exact model over wildcard
        exact = [p for p in candidates if p.model == model]
        return exact[0] if exact else candidates[0]


def provider_quota_enabled() -> bool:
    return provider_quota_is_enabled()


def allow_map_original_text_fallback(policy: Optional[QuotaPolicy] = None) -> bool:
    override = map_original_text_fallback_override()
    if override is not None:
        return override
    if policy is not None:
        return bool(policy.allow_map_original_text_fallback)
    return False
