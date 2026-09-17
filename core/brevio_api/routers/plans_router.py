"""Commercial plans catalog (read-only). Source: commercial_plans.yaml."""

from __future__ import annotations

from fastapi import APIRouter, status

from core.brevio_api.models.responses.plans_response import (
    PlanCatalogItem,
    PlansCatalogResponse,
)
from core.brevio_api.services.billing.plan_registry import get_plan_registry
from core.brevio_api.services.billing.stripe_service import get_cached_stripe_prices

router = APIRouter(prefix="/plans", tags=["plans"])


def _serialize_plan(plan, *, currency: str, highlighted_plan_id: str) -> PlanCatalogItem:
    amount = plan.list_price_monthly
    return PlanCatalogItem(
        plan_id=plan.plan_id,
        name=plan.name,
        version=plan.version,
        status=plan.status,
        documents_per_period=plan.documents_per_period,
        pages_per_document=plan.pages_per_document,
        pages_per_period=plan.pages_per_period,
        bytes_per_document=plan.bytes_per_document,
        bytes_per_audio=plan.bytes_per_audio,
        bytes_per_video=plan.bytes_per_video,
        bytes_per_period=plan.bytes_per_period,
        credits_per_period=plan.credits_per_period,
        rollover_max=plan.rollover_max,
        max_concurrent_jobs=plan.max_concurrent_jobs,
        scheduler_weight=plan.scheduler_weight,
        scheduler_priority=plan.scheduler_priority,
        byok_allowed=plan.byok_allowed,
        brevio_funded_models=list(plan.brevio_funded_models),
        funds_all_models=plan.funds_all_models,
        retention_days=plan.retention_days,
        media_enabled=plan.media_enabled,
        youtube_enabled=plan.youtube_enabled,
        price_amount=amount,
        price_currency=currency if amount is not None else None,
        billing_interval="month" if amount is not None else None,
        highlighted=plan.plan_id == highlighted_plan_id,
        cta_kind=plan.cta_kind,
        trial_days=plan.trial_days,
    )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=PlansCatalogResponse,
    summary="List active commercial plans",
    description=(
        "Public commercial plan catalog from commercial_plans.yaml. "
        "No authentication required. list_price_* values are marketing display "
        "amounts; checkout remains disabled until a billing provider is wired."
    ),
)
async def list_plans() -> PlansCatalogResponse:
    registry = get_plan_registry()
    pricing = registry.pricing
    plans = [
        _serialize_plan(
            plan,
            currency=pricing.currency,
            highlighted_plan_id=pricing.highlighted_plan_id,
        )
        for plan in registry.plans.values()
        if str(plan.status).lower() == "active"
    ]
    # Stable order: free → pro → business, then any other ids alphabetically.
    preferred = {"free": 0, "pro": 1, "business": 2}
    plans.sort(key=lambda p: (preferred.get(p.plan_id, 99), p.plan_id))
    
    # Inject dynamic Stripe prices if available
    dynamic_prices = await get_cached_stripe_prices()
    for plan in plans:
        if plan.plan_id in dynamic_prices:
            if "month" in dynamic_prices[plan.plan_id]:
                plan.price_amount = dynamic_prices[plan.plan_id]["month"]
            if "year" in dynamic_prices[plan.plan_id]:
                plan.annual_price_amount = dynamic_prices[plan.plan_id]["year"]

    return PlansCatalogResponse(
        default_plan_id=registry.default_plan_id,
        period_mode=registry.period_mode,
        rolling_days=registry.rolling_days,
        plan_change_usage_policy=registry.plan_change_usage_policy,
        checkout_enabled=False,
        billing_provider=None,
        customer_portal_enabled=False,
        show_billing_toggle=pricing.show_billing_toggle,
        annual_discount_percent=pricing.annual_discount_percent,
        sales_email=pricing.sales_email,
        highlighted_plan_id=pricing.highlighted_plan_id,
        plans=plans,
    )
