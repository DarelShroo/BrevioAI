"""ProviderCallExecutor: acquire → budget → call → release → sole retry path."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Awaitable, Callable, Optional

from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

from core.brevio.services.provider_quota.errors import (
    JobRequestBudgetExceededError,
    ProviderQuotaUnavailableError,
    QuotaAcquireTimeoutError,
)
from core.brevio.services.provider_quota.job_budget import JobRequestBudget
from core.brevio.services.provider_quota.manager import ProviderQuotaManager
from core.brevio.services.provider_quota.metrics import ProviderCallMetrics
from core.brevio.services.provider_quota.observability import (
    extract_rate_limit_signals,
    get_celery_task_id,
    log_provider_429,
)
from core.brevio.services.provider_quota.policy import QuotaPolicy
from core.brevio.services.provider_quota.retry import RetryCoordinator

logger = logging.getLogger(__name__)

CallFn = Callable[[], Awaitable[Any]]


def _request_may_have_reached_provider(exc: BaseException) -> bool:
    """
    Refund policy branches (explicit):

    - request never sent (local validation before call): allow_refund=True
      (handled by not acquiring / caller not using executor)

    - request sent + 429: allow_refund=False (may have counted input TPM/RPM)
    - request sent + timeout: allow_refund=False
    - request sent + 5xx: allow_refund=False
    - connection error with no response: allow_refund=True (conservative: often not counted)
    - success + usage known: allow_refund=True with settle to prompt_tokens
    - success + usage unknown: allow_refund=False for settle (keep reservation)
    """
    if isinstance(exc, QuotaAcquireTimeoutError):
        return False
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, APITimeoutError):
        return True
    if isinstance(exc, APIStatusError):
        return True
    if isinstance(exc, APIConnectionError):
        return False
    if isinstance(exc, asyncio.TimeoutError):
        return True
    if isinstance(exc, TimeoutError):
        return True
    return True


def _extract_prompt_tokens(response: Any) -> Optional[int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    prompt = getattr(usage, "prompt_tokens", None)
    if prompt is None and isinstance(usage, dict):
        prompt = usage.get("prompt_tokens")
    if prompt is None:
        return None
    try:
        return int(prompt)
    except (TypeError, ValueError):
        return None


class ProviderCallExecutor:
    def __init__(
        self,
        quota_manager: Optional[ProviderQuotaManager] = None,
        retry_coordinator: Optional[RetryCoordinator] = None,
        metrics: Optional[ProviderCallMetrics] = None,
        job_budget: Optional[JobRequestBudget] = None,
    ):
        self.metrics = metrics or ProviderCallMetrics()
        self.quota_manager = quota_manager or ProviderQuotaManager(metrics=self.metrics)
        if quota_manager is not None and metrics is not None:
            quota_manager.metrics = metrics
        self.retry = retry_coordinator or RetryCoordinator()
        self.job_budget = job_budget

    def bind_job(
        self,
        budget: Optional[JobRequestBudget],
        metrics: Optional[ProviderCallMetrics] = None,
    ) -> None:
        self.job_budget = budget
        if metrics is not None:
            self.metrics = metrics
            self.quota_manager.metrics = metrics

    async def _release_lease(
        self,
        *,
        lease_id: Optional[str],
        provider: str,
        model: str,
        quota_scope_id: str,
        reserved: int,
        actual_prompt: Optional[int],
        allow_refund: bool,
        policy: QuotaPolicy,
        phase: str,
        retry_number: int,
        chunk_id: Optional[str],
        call_succeeded: bool,
    ) -> None:
        if lease_id is None:
            return
        try:
            await self.quota_manager.release(
                provider=provider,
                model=model,
                quota_scope_id=quota_scope_id,
                lease_id=lease_id,
                reserved_input_tokens=reserved,
                actual_prompt_tokens=actual_prompt,
                allow_refund=allow_refund,
                policy=policy,
                call_succeeded=call_succeeded,
                phase=phase,
                retry_number=retry_number,
                chunk_id=chunk_id,
            )
        except Exception as release_err:
            logger.error(
                "event=provider_quota_release_on_error_failed error=%s",
                release_err,
            )

    async def execute(
        self,
        call: CallFn,
        *,
        provider: str,
        model: str,
        quota_scope_id: str,
        phase: str,
        estimated_input_tokens: int,
        chunk_id: Optional[str] = None,
        policy: Optional[QuotaPolicy] = None,
        job_budget: Optional[JobRequestBudget] = None,
        metrics: Optional[ProviderCallMetrics] = None,
    ) -> Any:
        policy = policy or self.quota_manager.resolve_policy(
            provider, model, quota_scope_id
        )
        budget = job_budget if job_budget is not None else self.job_budget
        stats = metrics if metrics is not None else self.metrics
        attempt = 0
        last_exc: Optional[BaseException] = None

        while attempt < policy.max_attempts:
            lease_id: Optional[str] = None
            reserved = max(0, int(estimated_input_tokens))
            allow_refund = False
            actual_prompt: Optional[int] = None
            call_succeeded = False
            try:
                lease_id, policy, _acq = await self.quota_manager.acquire(
                    provider=provider,
                    model=model,
                    quota_scope_id=quota_scope_id,
                    estimated_input_tokens=reserved,
                    policy=policy,
                    phase=phase,
                    retry_number=attempt,
                    chunk_id=chunk_id,
                )
                is_retry = attempt > 0
                if budget is not None:
                    try:
                        budget.consume_physical(is_retry=is_retry, phase=phase)
                    except JobRequestBudgetExceededError:
                        await self._release_lease(
                            lease_id=lease_id,
                            provider=provider,
                            model=model,
                            quota_scope_id=quota_scope_id,
                            reserved=reserved,
                            actual_prompt=None,
                            allow_refund=True,
                            policy=policy,
                            phase=phase,
                            retry_number=attempt,
                            chunk_id=chunk_id,
                            call_succeeded=False,
                        )
                        lease_id = None
                        raise
                    stats.apply_budget(
                        budget.physical, budget.remaining(), budget.expected_requests
                    )
                stats.record_physical(is_retry=is_retry, phase=phase)
                try:
                    response = await call()
                except BaseException:
                    # Ensure release on cancel/timeout before retry decision.
                    raise
                actual_prompt = _extract_prompt_tokens(response)
                allow_refund = actual_prompt is not None
                call_succeeded = True
                await self._release_lease(
                    lease_id=lease_id,
                    provider=provider,
                    model=model,
                    quota_scope_id=quota_scope_id,
                    reserved=reserved,
                    actual_prompt=actual_prompt,
                    allow_refund=allow_refund,
                    policy=policy,
                    phase=phase,
                    retry_number=attempt,
                    chunk_id=chunk_id,
                    call_succeeded=True,
                )
                lease_id = None
                stats.record_success(phase=phase)
                if budget is not None:
                    budget.record_success()
                return response
            except ProviderQuotaUnavailableError:
                raise
            except JobRequestBudgetExceededError:
                stats.record_failure(phase=phase)
                if budget is not None:
                    budget.record_failure()
                raise
            except Exception as e:
                last_exc = e
                may_reached = _request_may_have_reached_provider(e)
                allow_refund = not may_reached
                await self._release_lease(
                    lease_id=lease_id,
                    provider=provider,
                    model=model,
                    quota_scope_id=quota_scope_id,
                    reserved=reserved,
                    actual_prompt=None,
                    allow_refund=allow_refund,
                    policy=policy,
                    phase=phase,
                    retry_number=attempt,
                    chunk_id=chunk_id,
                    call_succeeded=False,
                )
                lease_id = None

                signals = extract_rate_limit_signals(e)
                is_429 = signals.status_code == 429 or isinstance(e, RateLimitError)
                if is_429:
                    stats.record_429(phase=phase)
                    log_provider_429(
                        signals=signals,
                        provider=provider,
                        model=model,
                        quota_scope_id=quota_scope_id,
                        phase=phase,
                        chunk_id=chunk_id,
                        retry_number=attempt,
                        worker_pid=os.getpid(),
                        celery_task_id=get_celery_task_id(),
                    )
                    wait_for_cd = signals.wait_seconds
                    if (
                        wait_for_cd is None
                        and policy.cooldown_on_429_seconds is not None
                    ):
                        wait_for_cd = policy.cooldown_on_429_seconds
                    if wait_for_cd and wait_for_cd > 0:
                        await self.quota_manager.apply_cooldown(
                            provider=provider,
                            model=model,
                            quota_scope_id=quota_scope_id,
                            wait_seconds=wait_for_cd,
                            policy=policy,
                        )

                cd_remaining = await self.quota_manager.cooldown_remaining_seconds(
                    provider=provider, model=model, quota_scope_id=quota_scope_id
                )
                decision = self.retry.decide(
                    exc=e,
                    attempt=attempt,
                    policy=policy,
                    signals=signals,
                    cooldown_remaining_seconds=cd_remaining,
                )
                is_acquire_timeout = isinstance(e, QuotaAcquireTimeoutError)
                if not is_acquire_timeout:
                    stats.record_failure(phase=phase)
                    if budget is not None:
                        budget.record_failure()
                if not decision.should_retry:
                    raise
                logger.info(
                    "[QUOTA] RETRY provider=%s model=%s phase=%s chunk=%s "
                    "retry=%s wait=%.3f reason=%s",
                    provider,
                    model,
                    phase,
                    chunk_id or "-",
                    attempt + 1,
                    decision.wait_seconds,
                    decision.reason,
                )
                await asyncio.sleep(decision.wait_seconds)
                attempt += 1
            except BaseException:
                # CancelledError / KeyboardInterrupt: release then re-raise.
                await self._release_lease(
                    lease_id=lease_id,
                    provider=provider,
                    model=model,
                    quota_scope_id=quota_scope_id,
                    reserved=reserved,
                    actual_prompt=None,
                    allow_refund=True,
                    policy=policy,
                    phase=phase,
                    retry_number=attempt,
                    chunk_id=chunk_id,
                    call_succeeded=False,
                )
                lease_id = None
                raise
            finally:
                # Belt-and-suspenders: never leave a lease held after the attempt.
                if lease_id is not None:
                    await self._release_lease(
                        lease_id=lease_id,
                        provider=provider,
                        model=model,
                        quota_scope_id=quota_scope_id,
                        reserved=reserved,
                        actual_prompt=actual_prompt if call_succeeded else None,
                        allow_refund=allow_refund if call_succeeded else True,
                        policy=policy,
                        phase=phase,
                        retry_number=attempt,
                        chunk_id=chunk_id,
                        call_succeeded=call_succeeded,
                    )
                    lease_id = None

        assert last_exc is not None
        raise last_exc
