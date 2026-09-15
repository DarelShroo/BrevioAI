"""Single retry/backoff owner for provider LLM calls."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

import httpx
from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

from core.brevio.services.provider_quota.errors import QuotaAcquireTimeoutError
from core.brevio.services.provider_quota.observability import RateLimitSignals
from core.brevio.services.provider_quota.policy import QuotaPolicy


@dataclass
class RetryDecision:
    should_retry: bool
    wait_seconds: float
    reason: str


class RetryCoordinator:
    """Sole retry layer. AsyncOpenAI must use max_retries=0."""

    RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}
    # Daily / project hard caps: Retry-After of ~60s cannot recover these.
    _DAILY_QUOTA_MARKERS = (
        "perday",
        "per_day",
        "requestsperday",
        "free_tier_requests",
        "generaterequestsperday",
    )

    @classmethod
    def is_daily_quota_exhausted(cls, signals: Optional[RateLimitSignals]) -> bool:
        if signals is None:
            return False
        blob = " ".join(
            str(part or "")
            for part in (
                signals.quota_id,
                signals.quota_metric,
                signals.reason,
                signals.error_code,
            )
        ).lower()
        compact = blob.replace("-", "").replace("_", "").replace(" ", "")
        return any(
            marker.replace("_", "") in compact for marker in cls._DAILY_QUOTA_MARKERS
        )

    def should_retry(
        self, exc: BaseException, attempt: int, policy: QuotaPolicy
    ) -> bool:
        if attempt >= policy.max_attempts:
            return False
        if isinstance(exc, QuotaAcquireTimeoutError):
            # max_in_flight / rpm / cooldown lease waits are transient capacity.
            return True
        if isinstance(exc, (RateLimitError, APIConnectionError, APITimeoutError)):
            return True
        if isinstance(exc, APIStatusError):
            return exc.status_code in self.RETRYABLE_STATUS
        if isinstance(exc, httpx.TimeoutException):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            code = exc.response.status_code if exc.response is not None else None
            return code in self.RETRYABLE_STATUS
        if isinstance(exc, TimeoutError):
            return True
        # Auth / bad request: do not retry
        return False

    def compute_wait_seconds(
        self,
        *,
        signals: Optional[RateLimitSignals],
        attempt: int,
        policy: QuotaPolicy,
        cooldown_remaining_seconds: float = 0.0,
    ) -> float:
        """
        Priority:
        1) Retry-After / retry-after-ms from signals
        2) admin cooldown_on_429_seconds when 429 and no header
        3) exponential backoff + jitter from policy
        Then take max with cooldown_remaining.
        """
        wait = 0.0
        if signals and signals.wait_seconds is not None:
            wait = max(0.0, float(signals.wait_seconds))
        elif (
            signals
            and signals.status_code == 429
            and policy.cooldown_on_429_seconds is not None
        ):
            wait = float(policy.cooldown_on_429_seconds)
        else:
            wait = self._backoff_with_jitter(attempt, policy)

        return max(wait, max(0.0, cooldown_remaining_seconds))

    def decide(
        self,
        *,
        exc: BaseException,
        attempt: int,
        policy: QuotaPolicy,
        signals: Optional[RateLimitSignals] = None,
        cooldown_remaining_seconds: float = 0.0,
    ) -> RetryDecision:
        if not self.should_retry(exc, attempt, policy):
            return RetryDecision(False, 0.0, "max_attempts_or_non_retryable")
        if self.is_daily_quota_exhausted(signals):
            return RetryDecision(False, 0.0, "daily_quota_exhausted")
        wait = self.compute_wait_seconds(
            signals=signals,
            attempt=attempt,
            policy=policy,
            cooldown_remaining_seconds=cooldown_remaining_seconds,
        )
        if isinstance(exc, QuotaAcquireTimeoutError):
            reason = f"quota_acquire_timeout:{exc.last_reason or 'unknown'}"
        elif signals and signals.wait_seconds is not None:
            reason = "retry_after"
        else:
            reason = "backoff"
        return RetryDecision(True, wait, reason)

    def _backoff_with_jitter(self, attempt: int, policy: QuotaPolicy) -> float:
        # attempt is 0-based for the failed try about to be retried
        exp = min(
            policy.backoff_max_seconds,
            policy.backoff_base_seconds * (2 ** max(attempt, 0)),
        )
        jitter = 1.0 - policy.jitter_ratio * random.random()
        return max(0.0, exp * jitter)
