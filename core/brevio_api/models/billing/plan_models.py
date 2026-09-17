"""Plan snapshot and product-period usage models (FASE 5)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pydantic import Field, field_validator

from core.shared.models.user.base_model import BaseModel, SerializedObjectId


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PlanSnapshot(BaseModel):
    """Immutable commercial config captured at job admission."""

    plan_id: str
    plan_version: str
    plan_name: str = ""
    documents_per_period: int = 0
    pages_per_document: int = 0
    pages_per_period: int = 0
    bytes_per_document: int = 0
    bytes_per_audio: int = 0
    bytes_per_video: int = 0
    bytes_per_period: int = 0
    credits_per_period: int = 0
    rollover_max: int = 0
    max_concurrent_jobs: int = 1
    byok_allowed: bool = True
    brevio_funded_models: List[str] = Field(default_factory=list)
    media_enabled: bool = False
    youtube_enabled: bool = False
    retention_days: int = 7
    scheduler_weight: int = 1
    scheduler_priority: int = 10
    captured_at: datetime = Field(default_factory=utcnow)

    @classmethod
    def from_plan(cls, plan) -> "PlanSnapshot":
        return cls(
            plan_id=plan.plan_id,
            plan_version=plan.version,
            plan_name=plan.name,
            documents_per_period=plan.documents_per_period,
            pages_per_document=plan.pages_per_document,
            pages_per_period=plan.pages_per_period,
            bytes_per_document=plan.bytes_per_document,
            bytes_per_audio=getattr(plan, "bytes_per_audio", 0),
            bytes_per_video=getattr(plan, "bytes_per_video", 0),
            bytes_per_period=plan.bytes_per_period,
            credits_per_period=plan.credits_per_period,
            rollover_max=getattr(plan, "rollover_max", 0),
            max_concurrent_jobs=plan.max_concurrent_jobs,
            byok_allowed=plan.byok_allowed,
            brevio_funded_models=list(plan.brevio_funded_models),
            media_enabled=plan.media_enabled,
            youtube_enabled=plan.youtube_enabled,
            retention_days=plan.retention_days,
            scheduler_weight=plan.scheduler_weight,
            scheduler_priority=plan.scheduler_priority,
        )


class ProductPeriodUsage(BaseModel):
    id: SerializedObjectId = Field(default_factory=ObjectId, alias="_id")
    user_id: SerializedObjectId
    plan_id: str
    plan_version: str
    period_start: datetime
    period_end: datetime
    documents_used: int = 0
    pages_used: int = 0
    bytes_used: int = 0
    credits_used: int = 0
    # FASE 6: credits_budget = credits_used + credits_hold_active (atomic gate).
    credits_hold_active: int = 0
    credits_budget: int = 0
    concurrent_jobs: int = 0
    version: int = 1
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    @field_validator(
        "documents_used",
        "pages_used",
        "bytes_used",
        "credits_used",
        "credits_hold_active",
        "credits_budget",
        "concurrent_jobs",
    )
    @classmethod
    def _non_neg(cls, value: int) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("must be int")
        if value < 0:
            raise ValueError("cannot be negative")
        return value


class ProductUsageRecord(BaseModel):
    """Idempotent product consumption per job (documents/pages/bytes once)."""

    id: SerializedObjectId = Field(default_factory=ObjectId, alias="_id")
    job_id: str
    user_id: SerializedObjectId
    plan_id: str
    plan_version: str
    period_start: datetime
    period_end: datetime
    documents: int = 0
    pages: int = 0
    bytes: int = 0
    credits: int = 0
    status: str = "RESERVED"  # RESERVED | COMMITTED | RELEASED
    # Frozen commercial config at first successful admit (survives plan upgrades).
    snapshot: Optional[PlanSnapshot] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
