"""Integration tests for Stripe billing HTTP router."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from core.brevio_api.__main__ import app
from core.brevio_api.dependencies.stripe_service_dependency import get_stripe_service
from core.brevio_api.dependencies.user_dependency import get_current_user
from core.brevio_api.dependencies.user_service_dependency import user_service_dependency


@pytest.fixture(autouse=True)
def cleanup_overrides():
    yield
    app.dependency_overrides.clear()


def test_billing_endpoints_require_authentication():
    client = TestClient(app)

    # Checkout requires auth
    res_checkout = client.post(
        "/billing/checkout",
        json={
            "plan_id": "pro",
            "billing_cycle": "month",
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel",
        },
    )
    assert res_checkout.status_code == 401

    # Portal requires auth
    res_portal = client.post(
        "/billing/portal",
        json={"return_url": "https://example.com/billing"},
    )
    assert res_portal.status_code == 401

    # Status requires auth
    res_status = client.get("/billing/status")
    assert res_status.status_code == 401

    # Sync requires auth
    res_sync = client.post("/billing/sync", json={})
    assert res_sync.status_code == 401


def test_webhook_missing_signature_returns_400():
    client = TestClient(app)
    res = client.post("/billing/webhook", content=b"{}")
    assert res.status_code == 400
    assert "MISSING_SIGNATURE" in res.text or res.status_code == 400


def test_webhook_with_valid_signature_returns_200():
    client = TestClient(app)
    mock_stripe_service = AsyncMock()
    mock_stripe_service.handle_webhook = AsyncMock()
    app.dependency_overrides[get_stripe_service] = lambda: mock_stripe_service

    res = client.post(
        "/billing/webhook",
        content=b'{"id": "evt_test_123"}',
        headers={"stripe-signature": "t=123,v1=test_sig"},
    )
    assert res.status_code == 200
    mock_stripe_service.handle_webhook.assert_awaited_once()


def test_billing_status_authenticated():
    client = TestClient(app)
    app.dependency_overrides[get_current_user] = lambda: "user123"

    mock_user = AsyncMock()
    mock_user.plan_id = "pro"
    mock_user.stripe_subscription_status = "active"

    mock_user_service = AsyncMock()
    mock_user_service.get_user_by_id = AsyncMock(return_value=mock_user)
    app.dependency_overrides[user_service_dependency] = lambda: mock_user_service

    res = client.get("/billing/status")
    assert res.status_code == 200
    data = res.json()
    assert data["plan_id"] == "pro"
    assert data["stripe_subscription_status"] == "active"
    assert data["has_active_subscription"] is True
