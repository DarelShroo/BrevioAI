"""Public commercial plan catalog responses (FASE 5 YAML)."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class PlanCatalogItem(BaseModel):
    plan_id: str
    name: str
    version: str
    status: str
    documents_per_period: int
    pages_per_document: int
    pages_per_period: int
    bytes_per_document: int
    bytes_per_audio: int
    bytes_per_video: int
    bytes_per_period: int
    credits_per_period: int
    rollover_max: int
    max_concurrent_jobs: int
    scheduler_weight: int
    scheduler_priority: int
    byok_allowed: bool
    brevio_funded_models: List[str] = Field(default_factory=list)
    funds_all_models: bool = False
    retention_days: int
    media_enabled: bool
    youtube_enabled: bool
    # Marketing list prices from YAML (not charged until checkout_enabled).
    price_amount: Optional[float] = None
    annual_price_amount: Optional[float] = None
    price_currency: Optional[str] = None
    billing_interval: Optional[str] = None
    highlighted: bool = False
    cta_kind: str = "start_free"
    trial_days: Optional[int] = None


class PlansCatalogResponse(BaseModel):
    status: str = "success"
    default_plan_id: str
    period_mode: str
    rolling_days: int
    plan_change_usage_policy: str
    checkout_enabled: bool = False
    billing_provider: Optional[str] = None
    customer_portal_enabled: bool = False
    show_billing_toggle: bool = False
    annual_discount_percent: int = 0
    sales_email: Optional[str] = None
    highlighted_plan_id: Optional[str] = None
    plans: List[PlanCatalogItem]
