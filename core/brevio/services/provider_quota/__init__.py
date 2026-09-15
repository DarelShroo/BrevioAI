"""Distributed provider quota orchestration (anti-429).

Google quotas (RPM / input TPM) are admin-configured from AI Studio.
Brevio operational controls (max_in_flight, lease TTL, cooldown) are separate.
RPD is intentionally deferred (Pacific midnight semantics).
"""

from core.brevio.services.provider_quota.errors import (
    JobRequestBudgetExceededError,
    ProviderQuotaError,
    ProviderQuotaUnavailableError,
    QuotaAcquireTimeoutError,
    QuotaPolicyMissingError,
)
from core.brevio.services.provider_quota.executor import ProviderCallExecutor
from core.brevio.services.provider_quota.job_budget import (
    JobRequestBudget,
    derive_job_max_provider_requests,
)
from core.brevio.services.provider_quota.metrics import ProviderCallMetrics
from core.brevio.services.provider_quota.observability import (
    RateLimitSignals,
    extract_rate_limit_signals,
    log_provider_429,
)
from core.brevio.services.provider_quota.policy import QuotaPolicy, load_quota_policies
from core.brevio.services.provider_quota.retry import RetryCoordinator

__all__ = [
    "JobRequestBudget",
    "JobRequestBudgetExceededError",
    "ProviderCallExecutor",
    "ProviderCallMetrics",
    "ProviderQuotaError",
    "ProviderQuotaUnavailableError",
    "QuotaAcquireTimeoutError",
    "QuotaPolicyMissingError",
    "QuotaPolicy",
    "RateLimitSignals",
    "RetryCoordinator",
    "derive_job_max_provider_requests",
    "extract_rate_limit_signals",
    "load_quota_policies",
    "log_provider_429",
]
