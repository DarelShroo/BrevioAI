"""Provider call metrics. Distinguishes physical HTTP from successes and retries."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PhaseCallMetrics:
    physical_http_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    retry_requests: int = 0
    provider_429_count: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "physical_http_requests": self.physical_http_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "retry_requests": self.retry_requests,
            "provider_429_count": self.provider_429_count,
        }


@dataclass
class ProviderCallMetrics:
    physical_http_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    retry_requests: int = 0
    rate_limit_waits: int = 0
    rate_limit_wait_seconds: float = 0.0
    provider_429_count: int = 0
    global_cooldown_count: int = 0
    connectivity_probes: int = 0
    job_request_budget_consumed: int = 0
    job_request_budget_remaining: int = 0
    job_expected_requests: int = 0
    by_phase: dict[str, PhaseCallMetrics] = field(default_factory=dict)

    def _phase(self, phase: str | None) -> PhaseCallMetrics:
        key = (phase or "UNKNOWN").upper()
        if key not in self.by_phase:
            self.by_phase[key] = PhaseCallMetrics()
        return self.by_phase[key]

    def record_physical(self, *, is_retry: bool, phase: str | None = None) -> None:
        self.physical_http_requests += 1
        phase_metrics = self._phase(phase)
        phase_metrics.physical_http_requests += 1
        if is_retry:
            self.retry_requests += 1
            phase_metrics.retry_requests += 1

    def record_success(self, *, phase: str | None = None) -> None:
        self.successful_requests += 1
        self._phase(phase).successful_requests += 1

    def record_failure(self, *, phase: str | None = None) -> None:
        self.failed_requests += 1
        self._phase(phase).failed_requests += 1

    def record_429(self, *, phase: str | None = None) -> None:
        self.provider_429_count += 1
        self._phase(phase).provider_429_count += 1

    def record_cooldown(self) -> None:
        self.global_cooldown_count += 1

    def record_wait(self, seconds: float) -> None:
        if seconds <= 0:
            return
        self.rate_limit_waits += 1
        self.rate_limit_wait_seconds += float(seconds)

    def record_probe(self) -> None:
        self.connectivity_probes += 1

    def apply_budget(self, consumed: int, remaining: int, expected: int) -> None:
        self.job_request_budget_consumed = consumed
        self.job_request_budget_remaining = remaining
        self.job_expected_requests = expected

    def as_dict(self) -> dict[str, int | float | dict[str, dict[str, int]]]:
        return {
            "physical_http_requests": self.physical_http_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "retry_requests": self.retry_requests,
            "rate_limit_waits": self.rate_limit_waits,
            "rate_limit_wait_seconds": round(self.rate_limit_wait_seconds, 3),
            "provider_429_count": self.provider_429_count,
            "global_cooldown_count": self.global_cooldown_count,
            "connectivity_probes": self.connectivity_probes,
            "job_request_budget_consumed": self.job_request_budget_consumed,
            "job_request_budget_remaining": self.job_request_budget_remaining,
            "job_expected_requests": self.job_expected_requests,
            "by_phase": {
                phase: metrics.as_dict()
                for phase, metrics in sorted(self.by_phase.items())
            },
        }
