"""Per-job hard cap on physical provider HTTP requests."""

from __future__ import annotations

from dataclasses import dataclass

from core.brevio.services.provider_quota.errors import JobRequestBudgetExceededError
from core.brevio.services.provider_quota.policy import QuotaPolicy
from core.shared.utils.environment import env_optional_int


def _env_int(name: str) -> int | None:
    return env_optional_int(name)


def derive_job_max_provider_requests(
    *,
    n_chunks: int,
    policy: QuotaPolicy,
    include_format: bool = True,
) -> int:
    """
    Hard cap for one summary job.

    Priority:
    1) QuotaPolicy.job_max_provider_requests
    2) JOB_MAX_PROVIDER_REQUESTS env
    3) derived from chunk count × retry attempts, plus REDUCE/FORMAT headroom

    Derived, not a magic Gemini number: MAP retries + bounded REDUCE splits + FORMAT.
    """
    configured = policy.job_max_provider_requests
    if configured is None:
        configured = _env_int("JOB_MAX_PROVIDER_REQUESTS")
    if configured is not None:
        return max(1, int(configured))

    chunks = max(0, int(n_chunks))
    attempts = max(1, int(policy.max_attempts))
    map_budget = chunks * attempts
    # REDUCE_SPLIT_SAFETY_CAP (16) × intermediate/final rounds, each retryable.
    reduce_budget = 16 * 6 * attempts
    format_budget = (4 * attempts) if include_format else 0
    return max(1, map_budget + reduce_budget + format_budget)


@dataclass
class JobRequestBudget:
    max_physical: int
    expected_requests: int = 0
    physical: int = 0
    retries: int = 0
    successes: int = 0
    failures: int = 0

    def remaining(self) -> int:
        return max(0, self.max_physical - self.physical)

    def consume_physical(self, *, is_retry: bool, phase: str) -> None:
        if self.physical >= self.max_physical:
            raise JobRequestBudgetExceededError(
                f"Job exceeded max provider requests "
                f"({self.physical}/{self.max_physical}) during {phase}"
            )
        self.physical += 1
        if is_retry:
            self.retries += 1

    def record_success(self) -> None:
        self.successes += 1

    def record_failure(self) -> None:
        self.failures += 1
