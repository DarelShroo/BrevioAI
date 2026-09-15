"""Resolved credential DTO — kept separate from CredentialResolver to avoid import cycles.

Consumers that only need the DTO (quota scope helpers, tests) should import from here
or from ``credential_resolver`` (which re-exports for the public API).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ResolvedCredential:
    api_key: str
    base_url: str
    is_platform: bool
    credential_id: str
    updated_at: datetime

    @property
    def quota_scope_id(self) -> str:
        """
        Safe quota identity for Redis/logs. Never the API key.

        Prefer admin override via QuotaPolicy.quota_scope (e.g. gcp-project:X).
        Fallback: platform | cred:{credential_id}.

        NOTE: Two user API keys belonging to the same Google Cloud project share
        Google's real project quota. Map them to the same gcp-project:X in YAML
        when the project id is known; cred:A and cred:B are NOT independent
        Google quotas.
        """
        from core.brevio.services.provider_quota.keys import build_quota_scope_id

        return build_quota_scope_id(
            is_platform=self.is_platform,
            credential_id=self.credential_id,
        )
