from __future__ import annotations

from typing import Optional


class ProviderQuotaError(Exception):
    """Base error for provider quota orchestration."""


class QuotaPolicyMissingError(ProviderQuotaError):
    """Raised when PROVIDER_QUOTA_ENABLED and no matching policy exists."""


class ProviderQuotaUnavailableError(ProviderQuotaError):
    """Raised when Redis/quota backend is unavailable (fail-closed)."""


class QuotaAcquireTimeoutError(ProviderQuotaError):
    """Raised when acquire cannot obtain a lease before timeout.

    Used for rate/cooldown/TPM denials (provider unavailable / paced).
    Waiting for max_in_flight capacity is a queue and must NOT raise this
    merely because other callers are active.
    """

    def __init__(
        self,
        message: str,
        *,
        last_reason: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_in_flight: Optional[int] = None,
    ):
        super().__init__(message)
        self.last_reason = last_reason
        self.provider = provider
        self.model = model
        self.max_in_flight = max_in_flight

    @property
    def is_max_in_flight(self) -> bool:
        return (self.last_reason or "") == "max_in_flight"


class JobRequestBudgetExceededError(ProviderQuotaError):
    """Raised when a summary job hits its hard cap of provider HTTP requests."""
