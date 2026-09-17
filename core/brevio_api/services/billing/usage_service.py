"""FASE 4: persist UsageRecord → CostRecord → consumed_credits for settlement."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId

from core.brevio_api.models.billing.usage_models import (
    CostRecord,
    UsageAttemptStatus,
    UsageRecord,
    UsageSource,
)
from core.brevio_api.repositories.billing.credit_repositories import (
    CreditReservationRepository,
    billing_collections,
)
from core.brevio_api.repositories.billing.usage_repositories import (
    CostRecordRepository,
    UsageRecordRepository,
    usage_billing_collections,
)
from core.brevio_api.services.billing.credit_service import (
    CreditService,
    SettlementResult,
)
from core.brevio.services.provider_quota.usage_normalize import (
    NormalizedUsage,
    normalize_provider_usage,
)
from core.shared.enums.model import ModelType
from core.shared.utils.pricing_registry import (
    calculate_actual_provider_cost,
    calculate_credits,
    convert_to_platform_currency,
    get_pricing_snapshot,
)

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ProviderAttemptEvent:
    job_id: str
    user_id: str
    provider: str
    model: str
    phase: str
    retry_index: int
    chunk_id: Optional[str]
    credential_scope: str
    status: str
    response: Any = None
    error: Optional[BaseException] = None
    is_fallback: bool = False
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class UsageBillingService:
    def __init__(
        self,
        usage_repo: UsageRecordRepository,
        cost_repo: CostRecordRepository,
        *,
        credit_service: Optional[CreditService] = None,
        reservations: Optional[CreditReservationRepository] = None,
    ) -> None:
        self.usage = usage_repo
        self.costs = cost_repo
        self.credits = credit_service
        self.reservations = reservations
        self._indexes_ready = False

    @classmethod
    def from_db(cls, db, *, credit_service: Optional[CreditService] = None) -> "UsageBillingService":
        cols = usage_billing_collections(db)
        bill = billing_collections(db)
        credits = credit_service or CreditService.from_db(db)
        return cls(
            UsageRecordRepository(cols["usage"]),
            CostRecordRepository(cols["costs"]),
            credit_service=credits,
            reservations=CreditReservationRepository(bill["reservations"]),
        )

    async def ensure_indexes(self) -> None:
        if self._indexes_ready:
            return
        await self.usage.ensure_indexes()
        await self.costs.ensure_indexes()
        self._indexes_ready = True

    @staticmethod
    def build_attempt_id(
        *,
        phase: str,
        chunk_id: Optional[str],
        retry_index: int,
        is_fallback: bool = False,
        provider: str = "",
    ) -> str:
        chunk = chunk_id or "-"
        fb = "1" if is_fallback else "0"
        return f"{phase}|{chunk}|r{retry_index}|fb{fb}|{provider}"

    async def record_provider_attempt(self, event: ProviderAttemptEvent) -> UsageRecord:
        """Idempotent UsageRecord + CostRecord for one physical provider attempt."""
        await self.ensure_indexes()
        attempt_id = self.build_attempt_id(
            phase=event.phase,
            chunk_id=event.chunk_id,
            retry_index=event.retry_index,
            is_fallback=event.is_fallback,
            provider=event.provider,
        )
        existing = await self.usage.get_by_attempt(event.job_id, attempt_id)
        if existing is not None:
            await self.ensure_cost_for_usage(existing)
            return existing

        normalized = normalize_provider_usage(event.response, exc=event.error)
        # Errors that never reached the provider should not invent usage.
        if event.status == UsageAttemptStatus.CANCELLED.value:
            normalized = NormalizedUsage(usage_source=UsageSource.UNAVAILABLE.value)

        record = UsageRecord(
            job_id=event.job_id,
            user_id=ObjectId(event.user_id),
            attempt_id=attempt_id,
            provider=event.provider,
            model=event.model,
            credential_scope=event.credential_scope or "unknown",
            phase=event.phase,
            status=event.status,
            usage_source=normalized.usage_source,
            input_tokens=normalized.input_tokens,
            output_tokens=normalized.output_tokens,
            total_tokens=normalized.total_tokens,
            cached_input_tokens=normalized.cached_input_tokens,
            reasoning_tokens=normalized.reasoning_tokens,
            audio_tokens=normalized.audio_tokens,
            retry_index=event.retry_index,
            is_retry=event.retry_index > 0,
            is_fallback=event.is_fallback,
            chunk_id=event.chunk_id,
            provider_request_id=normalized.provider_request_id,
            finish_reason=normalized.finish_reason,
            error_type=type(event.error).__name__ if event.error else None,
            started_at=event.started_at or utcnow(),
            completed_at=event.completed_at or utcnow(),
        )
        created = await self.usage.create(record)
        await self.ensure_cost_for_usage(created)
        logger.info(
            "event=usage_record_created job_id=%s attempt_id=%s provider=%s "
            "model=%s phase=%s status=%s usage_source=%s input=%s output=%s",
            created.job_id,
            created.attempt_id,
            created.provider,
            created.model,
            created.phase,
            created.status,
            created.usage_source,
            created.input_tokens,
            created.output_tokens,
        )
        return created

    def _resolve_model_type(self, model: str) -> Optional[ModelType]:
        try:
            return ModelType(model)
        except ValueError:
            for item in ModelType:
                if item.value == model or item.name == model:
                    return item
        return None

    async def ensure_cost_for_usage(self, usage: UsageRecord) -> Optional[CostRecord]:
        await self.ensure_indexes()
        existing = await self.costs.get_by_usage_id(str(usage.id))
        if existing is not None:
            return existing

        if usage.usage_source == UsageSource.UNAVAILABLE.value:
            # Persist a zero-cost row so uniqueness and audit remain complete.
            cost = CostRecord(
                job_id=usage.job_id,
                usage_id=usage.id,
                user_id=usage.user_id,
                provider=usage.provider,
                model=usage.model,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cached_input_tokens=usage.cached_input_tokens,
                provider_cost=0.0,
                platform_cost=0.0,
                credits=0,
                usage_source=usage.usage_source,
                pricing_version="",
                pricing_source="unavailable",
                metadata={"note": "no_billable_usage"},
            )
            created = await self.costs.create(cost)
            return created

        model_type = self._resolve_model_type(usage.model)
        if model_type is None:
            logger.warning(
                "event=cost_record_skipped job_id=%s usage_id=%s reason=unknown_model model=%s",
                usage.job_id,
                usage.id,
                usage.model,
            )
            return None

        snapshot = get_pricing_snapshot(model_type)
        provider_cost = calculate_actual_provider_cost(
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_input_tokens=usage.cached_input_tokens,
            snapshot=snapshot,
        )
        platform_cost = convert_to_platform_currency(provider_cost, snapshot)
        if usage.input_tokens == 0 and usage.output_tokens == 0:
            credits = 0
        else:
            credits = calculate_credits(platform_cost, snapshot)
        if usage.usage_source == UsageSource.ESTIMATED.value:
            # Estimated usage still produces a cost row but is flagged.
            pass

        cost = CostRecord(
            job_id=usage.job_id,
            usage_id=usage.id,
            user_id=usage.user_id,
            provider=usage.provider,
            model=usage.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_input_tokens=usage.cached_input_tokens,
            input_unit_price=snapshot.input_price_per_million,
            output_unit_price=snapshot.output_price_per_million,
            cached_input_unit_price=snapshot.cached_input_price_per_million,
            provider_cost=round(provider_cost, 10),
            platform_cost=platform_cost,
            currency=snapshot.currency,
            platform_currency=snapshot.platform_currency,
            credits=int(credits),
            pricing_version=snapshot.pricing_version,
            pricing_source="pricing_registry",
            usage_source=usage.usage_source,
        )
        created = await self.costs.create(cost)
        logger.info(
            "event=cost_record_created job_id=%s usage_id=%s provider_cost=%s "
            "platform_cost=%s credits=%s pricing_version=%s",
            created.job_id,
            created.usage_id,
            created.provider_cost,
            created.platform_cost,
            created.credits,
            created.pricing_version,
        )
        return created

    async def calculate_job_consumed_credits(self, job_id: str) -> int:
        """Sum CostRecord.credits for the job (all billing modes)."""
        await self.ensure_indexes()

        costs = await self.costs.list_by_job(job_id)
        if not costs:
            # Ensure costs exist for any usage rows (recovery path).
            usages = await self.usage.list_by_job(job_id)
            for usage in usages:
                await self.ensure_cost_for_usage(usage)
            costs = await self.costs.list_by_job(job_id)

        total = 0
        for cost in costs:
            total += int(cost.credits or 0)
        if total < 0:
            total = 0
        logger.info(
            "event=job_usage_aggregated job_id=%s consumed_credits=%s cost_rows=%s",
            job_id,
            total,
            len(costs),
        )
        return total

    async def settle_job_from_usage(self, job_id: str) -> SettlementResult:
        if self.credits is None:
            raise RuntimeError("CreditService required for settlement")
        consumed = await self.calculate_job_consumed_credits(job_id)
        return await self.credits.settle_job(
            job_id=job_id,
            consumed_credits=consumed,
            metadata={"source": "fase4_real_usage"},
        )
