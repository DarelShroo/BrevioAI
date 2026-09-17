"""Product limits admission (FASE 5). Independent from CreditAccount."""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from bson import ObjectId

from core.brevio_api.models.billing.plan_models import (
    PlanSnapshot,
    ProductUsageRecord,
    utcnow,
)
from core.brevio_api.models.errors.api_codes import ApiErrorCode, CodedHTTPException
from core.brevio_api.repositories.billing.plan_repositories import (
    ProductPeriodUsageRepository,
    ProductUsageRecordRepository,
    product_billing_collections,
)
from core.brevio_api.services.billing.plan_registry import (
    PlanDefinition,
    default_plan,
    get_plan,
    get_plan_registry,
)
from core.shared.enums.model import ModelType
from core.shared.utils.model_catalog import model_requires_api_key

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DocumentMetrics:
    filename: str
    bytes_size: int
    pages: int


@dataclass(frozen=True)
class AdmissionRequest:
    user_id: str
    job_id: str
    source_type: str
    model: ModelType
    has_byok: bool
    documents: List[DocumentMetrics]


@dataclass(frozen=True)
class AdmissionResult:
    plan: PlanDefinition
    snapshot: PlanSnapshot
    period_start: datetime
    period_end: datetime
    documents: int
    pages: int
    bytes_total: int
    product_record: ProductUsageRecord


def current_period_bounds(
    *, now: Optional[datetime] = None
) -> Tuple[datetime, datetime]:
    """Calendar month UTC by default; rolling_days when configured.

    Decision (FASE 5): default = calendar_month (UTC). rolling_days is
    supported via commercial_plans.yaml period_mode without rewriting callers.
    """
    now = now or datetime.now(timezone.utc)
    registry = get_plan_registry()
    if registry.period_mode == "rolling_days":
        from datetime import timedelta

        # Floor to UTC midnight so (user_id, start, end) is stable for the day.
        # Wall-clock `now` as end would mint a new period doc per admit → unlimited.
        days = max(1, int(registry.rolling_days or 30))
        end = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) + timedelta(
            days=1
        )
        start = end - timedelta(days=days)
        return start, end
    start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    if now.month == 12:
        end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
    return start, end


def measure_documents(
    files_data: List[Tuple[str, bytes]], *, source_type: str
) -> List[DocumentMetrics]:
    """Per-file bytes + pages. PDF uses page count; other docs count as 1 page."""
    out: List[DocumentMetrics] = []
    if source_type in {"media", "youtube"} and not files_data:
        return [DocumentMetrics(filename="youtube", bytes_size=0, pages=0)]
    for filename, content in files_data:
        size = len(content or b"")
        pages = 1
        lower = (filename or "").lower()
        if lower.endswith(".pdf") and content:
            try:
                import pypdf

                reader = pypdf.PdfReader(io.BytesIO(content))
                pages = max(1, len(reader.pages))
            except Exception:
                pages = 1
        if source_type in {"media", "youtube"}:
            pages = 0
        out.append(DocumentMetrics(filename=filename, bytes_size=size, pages=pages))
    return out


class ProductLimitError(CodedHTTPException):
    def __init__(self, code: ApiErrorCode, detail: str | None = None):
        super().__init__(status_code=403, code=code, detail=detail or code.value)


class ProductLimitService:
    def __init__(
        self,
        periods: ProductPeriodUsageRepository,
        records: ProductUsageRecordRepository,
    ) -> None:
        self.periods = periods
        self.records = records
        self._ready = False

    @classmethod
    def from_db(cls, db) -> "ProductLimitService":
        cols = product_billing_collections(db)
        return cls(
            ProductPeriodUsageRepository(cols["period_usage"]),
            ProductUsageRecordRepository(cols["product_usage"]),
        )

    async def ensure_indexes(self) -> None:
        if self._ready:
            return
        await self.periods.ensure_indexes()
        await self.records.ensure_indexes()
        self._ready = True

    def resolve_user_plan(self, user) -> PlanDefinition:
        plan_id = getattr(user, "plan_id", None) or default_plan().plan_id
        try:
            return get_plan(str(plan_id))
        except KeyError:
            logger.warning("event=unknown_plan_fallback plan_id=%s", plan_id)
            return default_plan()

    def check_source_and_model(
        self, plan: PlanDefinition, *, source_type: str, model: ModelType, has_byok: bool
    ) -> None:
        if source_type == "media" and not plan.media_enabled:
            raise ProductLimitError(ApiErrorCode.MEDIA_DISABLED)
        if source_type == "youtube" and not plan.youtube_enabled:
            raise ProductLimitError(ApiErrorCode.YOUTUBE_DISABLED)
        if has_byok:
            if not plan.byok_allowed:
                raise ProductLimitError(ApiErrorCode.BYOK_NOT_ALLOWED)
            return
        # Platform-funded path: model must be in funded list (or all if empty).
        if model_requires_api_key(model) and not plan.funds_model(model.value):
            raise ProductLimitError(ApiErrorCode.MODEL_NOT_FUNDED)

    def check_per_document(
        self,
        plan: PlanDefinition,
        docs: List[DocumentMetrics],
        *,
        source_type: str = "documents",
    ) -> None:
        for doc in docs:
            if source_type not in {"media", "youtube"} and doc.pages > plan.pages_per_document:
                raise ProductLimitError(ApiErrorCode.PLAN_PAGE_LIMIT)
            limit = plan.max_upload_bytes_for_source(source_type, doc.filename)
            if doc.bytes_size > limit:
                raise ProductLimitError(ApiErrorCode.PLAN_BYTES_LIMIT)

    async def admit(self, request: AdmissionRequest, *, plan: PlanDefinition) -> AdmissionResult:
        """Atomic product-limit reservation bound to job_id (idempotent)."""
        await self.ensure_indexes()
        existing = await self.records.get_by_job(request.job_id)
        if existing is not None:
            snapshot = existing.snapshot or PlanSnapshot(
                plan_id=existing.plan_id,
                plan_version=existing.plan_version,
            )
            return AdmissionResult(
                plan=plan,
                snapshot=snapshot,
                period_start=existing.period_start,
                period_end=existing.period_end,
                documents=existing.documents,
                pages=existing.pages,
                bytes_total=existing.bytes,
                product_record=existing,
            )

        self.check_source_and_model(
            plan,
            source_type=request.source_type,
            model=request.model,
            has_byok=request.has_byok,
        )
        self.check_per_document(
            plan, request.documents, source_type=request.source_type
        )

        documents = len(request.documents)
        pages = sum(d.pages for d in request.documents)
        bytes_total = sum(d.bytes_size for d in request.documents)
        if documents <= 0:
            raise ProductLimitError(ApiErrorCode.PLAN_DOCUMENT_LIMIT)

        period_start, period_end = current_period_bounds()
        # Hold 1 period-credit unit at admit for every job (atomic with docs/pages).
        # Real CostRecord credits are settled later into credits_used / CreditAccount.
        credits_hold = 1

        updated = await self.periods.atomic_reserve(
            user_id=request.user_id,
            period_start=period_start,
            period_end=period_end,
            plan_id=plan.plan_id,
            plan_version=plan.version,
            documents=documents,
            pages=pages,
            bytes_amount=bytes_total,
            documents_limit=plan.documents_per_period,
            pages_limit=plan.pages_per_period,
            bytes_limit=plan.bytes_per_period,
            concurrent_limit=plan.max_concurrent_jobs,
            credits_hold=credits_hold,
            credits_limit=plan.rollover_max,
        )
        if updated is None:
            # Distinguish concurrency vs period by peeking.
            current = await self.periods.get_period(
                request.user_id, period_start, period_end
            )
            if current and current.concurrent_jobs >= plan.max_concurrent_jobs:
                raise ProductLimitError(ApiErrorCode.PLAN_CONCURRENCY_LIMIT)
            if current and current.documents_used + documents > plan.documents_per_period:
                raise ProductLimitError(ApiErrorCode.PLAN_DOCUMENT_LIMIT)
            if current and current.pages_used + pages > plan.pages_per_period:
                raise ProductLimitError(ApiErrorCode.PLAN_PAGE_LIMIT)
            if current and current.bytes_used + bytes_total > plan.bytes_per_period:
                raise ProductLimitError(ApiErrorCode.PLAN_BYTES_LIMIT)
            raise ProductLimitError(ApiErrorCode.PLAN_PERIOD_LIMIT)

        snapshot = PlanSnapshot.from_plan(plan)
        record = ProductUsageRecord(
            job_id=request.job_id,
            user_id=ObjectId(request.user_id),
            plan_id=plan.plan_id,
            plan_version=plan.version,
            period_start=period_start,
            period_end=period_end,
            documents=documents,
            pages=pages,
            bytes=bytes_total,
            status="RESERVED",
            snapshot=snapshot,
            metadata={
                "source_type": request.source_type,
                "model": request.model.value,
                "credits_hold": credits_hold,
            },
        )
        try:
            created = await self.records.create(record)
        except Exception:
            await self.periods.rollback_reserve(
                user_id=request.user_id,
                period_start=period_start,
                period_end=period_end,
                documents=documents,
                pages=pages,
                bytes_amount=bytes_total,
                release_concurrency=True,
                credits_hold=credits_hold,
            )
            raise

        if str(created.id) != str(record.id):
            # Duplicate job won — rollback our period increment.
            await self.periods.rollback_reserve(
                user_id=request.user_id,
                period_start=period_start,
                period_end=period_end,
                documents=documents,
                pages=pages,
                bytes_amount=bytes_total,
                release_concurrency=True,
                credits_hold=credits_hold,
            )
            return AdmissionResult(
                plan=plan,
                snapshot=created.snapshot
                or PlanSnapshot(
                    plan_id=created.plan_id, plan_version=created.plan_version
                ),
                period_start=created.period_start,
                period_end=created.period_end,
                documents=created.documents,
                pages=created.pages,
                bytes_total=created.bytes,
                product_record=created,
            )

        logger.info(
            "event=product_limit_reserved user_id=%s job_id=%s plan=%s "
            "docs=%s pages=%s bytes=%s",
            request.user_id,
            request.job_id,
            plan.plan_id,
            documents,
            pages,
            bytes_total,
        )
        return AdmissionResult(
            plan=plan,
            snapshot=snapshot,
            period_start=period_start,
            period_end=period_end,
            documents=documents,
            pages=pages,
            bytes_total=bytes_total,
            product_record=created,
        )

    async def release_admission(self, job_id: str) -> None:
        """Roll back product counters if job never ran / admission aborted."""
        record = await self.records.get_by_job(job_id)
        if record is None:
            return
        if record.status != "RESERVED":
            return
        updated = await self.records.mark_status(
            job_id, from_status="RESERVED", to_status="RELEASED"
        )
        if updated is None:
            return
        hold = int((record.metadata or {}).get("credits_hold") or 0)
        await self.periods.rollback_reserve(
            user_id=str(record.user_id),
            period_start=record.period_start,
            period_end=record.period_end,
            documents=record.documents,
            pages=record.pages,
            bytes_amount=record.bytes,
            release_concurrency=True,
            credits_hold=hold,
        )

    async def commit_admission(self, job_id: str) -> None:
        """Mark product usage committed (documents count permanently).

        Concurrency slot is released only when RESERVED→COMMITTED wins (CAS),
        so idempotent / replayed commit cannot decrement another job's slot.
        """
        record = await self.records.get_by_job(job_id)
        if record is None:
            return
        updated = await self.records.mark_status(
            job_id, from_status="RESERVED", to_status="COMMITTED"
        )
        if updated is None:
            return
        await self.periods.release_concurrency(
            str(record.user_id), record.period_start, record.period_end
        )

    async def record_settled_credits(
        self, job_id: str, consumed_credits: int, *, credits_limit: int
    ) -> None:
        """credits_used derives from settlement, not reservation."""
        record = await self.records.get_by_job(job_id)
        if record is None:
            return
        if record.credits > 0:
            return  # already applied
        credits = max(0, int(consumed_credits))
        hold = int((record.metadata or {}).get("credits_hold") or 0)
        from pymongo import ReturnDocument

        doc = await self.records.collection.find_one_and_update(
            {"job_id": job_id, "credits": 0},
            {"$set": {"credits": credits, "updated_at": utcnow()}},
            return_document=ReturnDocument.AFTER,
        )
        if not doc:
            return
        if hold > 0:
            await self.periods.release_credits_hold(
                user_id=str(record.user_id),
                period_start=record.period_start,
                period_end=record.period_end,
                hold=hold,
            )
        if credits > 0:
            await self.periods.atomic_add_credits(
                user_id=str(record.user_id),
                period_start=record.period_start,
                period_end=record.period_end,
                credits=credits,
                credits_limit=credits_limit,
            )

    async def entitlements(self, user, *, credit_balance: int | None = None) -> dict:
        await self.ensure_indexes()
        plan = self.resolve_user_plan(user)
        period_start, period_end = current_period_bounds()
        usage = await self.periods.get_period(str(user.id), period_start, period_end)
        docs_used = usage.documents_used if usage else 0
        pages_used = usage.pages_used if usage else 0
        bytes_used = usage.bytes_used if usage else 0
        credits_used = usage.credits_used if usage else 0
        concurrent = usage.concurrent_jobs if usage else 0
        # Wallet balance is the commercial available pool (includes rollover).
        # Period credits_used tracks settlement within the calendar window.
        if credit_balance is not None:
            credits_remaining = max(0, int(credit_balance))
            implied_used = max(0, credits_used)
        else:
            credits_remaining = max(0, plan.credits_per_period - credits_used)
            implied_used = credits_used
        registry = get_plan_registry()
        return {
            "plan_id": plan.plan_id,
            "plan_name": plan.name,
            "plan_version": plan.version,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "period_mode": registry.period_mode,
            "rolling_days": registry.rolling_days,
            "plan_change_usage_policy": registry.plan_change_usage_policy,
            "limits": {
                "documents_per_period": plan.documents_per_period,
                "pages_per_document": plan.pages_per_document,
                "pages_per_period": plan.pages_per_period,
                "bytes_per_document": plan.bytes_per_document,
                "bytes_per_audio": plan.bytes_per_audio,
                "bytes_per_video": plan.bytes_per_video,
                "bytes_per_period": plan.bytes_per_period,
                "credits_per_period": plan.credits_per_period,
                "rollover_max": plan.rollover_max,
                "max_concurrent_jobs": plan.max_concurrent_jobs,
                "media_enabled": plan.media_enabled,
                "youtube_enabled": plan.youtube_enabled,
                "byok_allowed": plan.byok_allowed,
                "retention_days": plan.retention_days,
                "brevio_funded_models": list(plan.brevio_funded_models),
                "funds_all_models": plan.funds_all_models,
            },
            "usage": {
                "documents_used": docs_used,
                "pages_used": pages_used,
                "bytes_used": bytes_used,
                "credits_used": implied_used,
                "concurrent_jobs": concurrent,
            },
            "remaining": {
                "documents": max(0, plan.documents_per_period - docs_used),
                "pages": max(0, plan.pages_per_period - pages_used),
                "bytes": max(0, plan.bytes_per_period - bytes_used),
                "credits": credits_remaining,
                "concurrent_jobs": max(0, plan.max_concurrent_jobs - concurrent),
            },
        }
