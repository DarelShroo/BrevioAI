import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from bson import ObjectId

from core.brevio_api.__main__ import app
from core.brevio_api.models.user.user_model import User
from core.brevio_api.dependencies.user_dependency import get_current_user
from core.brevio_api.dependencies.user_service_dependency import user_service_dependency
from core.brevio_api.dependencies.stripe_service_dependency import get_stripe_service

@pytest.fixture
def mock_user():
    return User(
        _id=ObjectId(),
        username="testuser",
        email="test@example.com",
        password="hashed",
        stripe_customer_id="cus_123",
        plan_id="free",
        stripe_subscription_status=None
    )

@pytest.fixture
def mock_stripe_service():
    mock_service = AsyncMock()
    mock_service.create_checkout_session.return_value = "https://checkout.stripe.com/test"
    mock_service.create_portal_session.return_value = "https://billing.stripe.com/test"
    mock_service.handle_webhook.return_value = None
    return mock_service

@pytest.fixture
def client(mock_user, mock_stripe_service):
    mock_user_service = AsyncMock()
    mock_user_service.get_user_by_id.return_value = mock_user

    app.dependency_overrides[get_current_user] = lambda: str(mock_user.id)
    app.dependency_overrides[user_service_dependency] = lambda: mock_user_service
    app.dependency_overrides[get_stripe_service] = lambda: mock_stripe_service
    
    with patch("core.brevio_api.core.database.AsyncDB.verify_connection", new_callable=AsyncMock):
        with TestClient(app) as test_client:
            yield test_client
    app.dependency_overrides = {}

def test_create_checkout_session(client, mock_stripe_service, mock_user):
    response = client.post(
        "/billing/checkout",
        json={
            "plan_id": "pro",
            "billing_cycle": "month",
            "success_url": "http://localhost/success",
            "cancel_url": "http://localhost/cancel"
        }
    )
    
    assert response.status_code == 200
    assert response.json() == {"url": "https://checkout.stripe.com/test"}
    mock_stripe_service.create_checkout_session.assert_called_once_with(
        user=mock_user,
        plan_id="pro",
        billing_cycle="month",
        success_url="http://localhost/success",
        cancel_url="http://localhost/cancel"
    )

def test_create_portal_session(client, mock_stripe_service, mock_user):
    response = client.post(
        "/billing/portal",
        json={
            "return_url": "http://localhost/profile"
        }
    )
    
    assert response.status_code == 200
    assert response.json() == {"url": "https://billing.stripe.com/test"}
    mock_stripe_service.create_portal_session.assert_called_once_with(
        user=mock_user,
        return_url="http://localhost/profile"
    )

def test_webhook_missing_signature(client):
    response = client.post(
        "/billing/webhook",
        content=b"{}",
        headers={}
    )
    assert response.status_code == 400
    assert "Missing signature" in response.text

def test_webhook_success(client, mock_stripe_service):
    response = client.post(
        "/billing/webhook",
        content=b'{"id": "evt_test", "type": "checkout.session.completed"}',
        headers={"stripe-signature": "t=123,v1=abc"}
    )
    assert response.status_code == 200
    mock_stripe_service.handle_webhook.assert_called_once()
    
def test_get_billing_status(client, mock_user):
    response = client.get("/billing/status")
    assert response.status_code == 200
    data = response.json()
    assert data["plan_id"] == "free"
    assert data["stripe_subscription_status"] is None
    assert data["has_active_subscription"] is False


def test_sync_billing_state(client, mock_stripe_service, mock_user):
    mock_stripe_service.sync_user_subscription.return_value = {
        "plan_id": "pro",
        "synced": True,
        "credits_balance": 4000,
    }
    response = client.post("/billing/sync", json={"session_id": "cs_test_abc"})
    assert response.status_code == 200
    data = response.json()
    assert data["plan_id"] == "pro"
    assert data["synced"] is True
    mock_stripe_service.sync_user_subscription.assert_called_once_with(
        mock_user, session_id="cs_test_abc"
    )
