"""GET /plans catalog from commercial_plans.yaml (public)."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from core.brevio_api.__main__ import app
from core.brevio_api.services.billing.plan_registry import (
    clear_plan_registry_cache,
    get_plan_registry,
)


@pytest.fixture(autouse=True)
def clear_overrides_and_cache() -> None:
    clear_plan_registry_cache()
    yield
    app.dependency_overrides.clear()
    clear_plan_registry_cache()


def test_list_plans_is_public() -> None:
    client = TestClient(app)
    with patch(
        "core.brevio_api.routers.plans_router.get_cached_stripe_prices",
        new=AsyncMock(return_value={}),
    ):
        response = client.get("/plans")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["default_plan_id"] == "free"
    assert body["period_mode"] == "calendar_month"
    assert body["plan_change_usage_policy"] == "keep_period_counters"
    assert body["checkout_enabled"] is False
    assert body["billing_provider"] is None
    assert body["customer_portal_enabled"] is False

    registry = get_plan_registry()
    plan_ids = [p["plan_id"] for p in body["plans"]]
    expected = [
        pid
        for pid, plan in registry.plans.items()
        if str(plan.status).lower() == "active"
    ]
    assert set(plan_ids) == set(expected)
    assert plan_ids[:3] == ["free", "pro", "business"] or set(plan_ids) == set(expected)

    by_id = {p["plan_id"]: p for p in body["plans"]}
    free = by_id["free"]
    assert free["name"] == "Free"
    assert free["credits_per_period"] == registry.plans["free"].credits_per_period
    assert free["documents_per_period"] == 10
    assert free["media_enabled"] is True
    assert free["youtube_enabled"] is False
    assert free["byok_allowed"] is True
    assert free["credits_per_period"] == 100
    assert free["rollover_max"] == 200
    assert free["pages_per_document"] == 200
    assert free["pages_per_period"] == 1000
    assert free["bytes_per_document"] == 25 * 1024 * 1024
    assert free["bytes_per_audio"] == 50 * 1024 * 1024
    assert free["bytes_per_video"] == 250 * 1024 * 1024
    assert free["max_concurrent_jobs"] == 5
    assert free["price_amount"] == 0
    assert free["price_currency"] == "EUR"
    assert free["billing_interval"] == "month"
    assert free["cta_kind"] == "start_free"

    pro = by_id["pro"]
    assert pro["media_enabled"] is True
    assert pro["youtube_enabled"] is True
    assert pro["credits_per_period"] == 4000
    assert pro["rollover_max"] == 8000
    assert pro["documents_per_period"] == 100
    assert pro["pages_per_document"] == 1000
    assert pro["pages_per_period"] == 10000
    assert pro["bytes_per_document"] == 100 * 1024 * 1024
    assert pro["bytes_per_audio"] == 250 * 1024 * 1024
    assert pro["bytes_per_video"] == 2 * 1024 * 1024 * 1024
    assert pro["max_concurrent_jobs"] == 20
    assert "gpt-4o-mini" in pro["brevio_funded_models"]
    assert pro["price_amount"] == 9.99
    assert pro["highlighted"] is True
    assert pro["cta_kind"] == "choose_pro"

    business = by_id["business"]
    assert business["funds_all_models"] is True
    assert business["brevio_funded_models"] == []
    assert business["credits_per_period"] == 20000
    assert business["rollover_max"] == 40000
    assert business["documents_per_period"] == 500
    assert business["pages_per_document"] == 5000
    assert business["pages_per_period"] == 50000
    assert business["bytes_per_document"] == 500 * 1024 * 1024
    assert business["bytes_per_audio"] == 1 * 1024 * 1024 * 1024
    assert business["bytes_per_video"] == 10 * 1024 * 1024 * 1024
    assert business["max_concurrent_jobs"] == 50
    assert business["byok_allowed"] is True
    assert business["price_amount"] == 19.99
    assert business["cta_kind"] == "contact_sales"

    assert body["show_billing_toggle"] is True
    assert body["annual_discount_percent"] == 20
    assert body["sales_email"] == "support@brevio.com"
    assert body["highlighted_plan_id"] == "pro"
    assert body["checkout_enabled"] is False
