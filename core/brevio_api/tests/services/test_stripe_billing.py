"""Comprehensive tests for Stripe Billing integration (FASE 6)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import stripe
from bson import ObjectId
from fastapi import HTTPException
from mongomock_motor import AsyncMongoMockClient

from core.brevio_api.models.billing.stripe_event_model import StripeWebhookEvent
from core.brevio_api.models.user.user_model import User
from core.brevio_api.repositories.billing.stripe_event_repository import (
    StripeEventRepository,
)
from core.brevio_api.repositories.user_repository import UserRepository
from core.brevio_api.services.billing.stripe_service import (
    StripeConfig,
    StripeService,
)
from core.brevio_api.services.user_service import UserService


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client.get_database("billing_test_db")


@pytest.fixture
def mock_user():
    return User(
        id=ObjectId(),
        email="customer@example.com",
        username="paying_user",
        password="secret_hashed_password",
        plan_id="free",
        plan_version="1",
        stripe_customer_id=None,
        stripe_subscription_id=None,
        stripe_subscription_status=None,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def stripe_service(db, mock_user):
    user_repo = MagicMock(spec=UserRepository)
    user_repo.update_user = AsyncMock(return_value=mock_user)
    user_repo.get_user_by_id = AsyncMock(return_value=mock_user)
    user_repo.get_user_by_field = AsyncMock(return_value=mock_user)

    folder_repo = MagicMock()
    user_service = UserService(user_repo, folder_repo)
    user_service.get_user_by_id = AsyncMock(return_value=mock_user)
    user_service.get_user_by_stripe_customer_id = AsyncMock(return_value=mock_user)

    event_coll = db["stripe_webhook_events"]
    stripe_event_repo = StripeEventRepository(event_coll)

    credit_service = MagicMock()
    credit_service.grant_subscription_credits = AsyncMock(return_value=True)
    credit_service.get_balance = AsyncMock(return_value=4000)

    service = StripeService(
        user_service=user_service,
        stripe_event_repo=stripe_event_repo,
        credit_service=credit_service,
    )
    service.config.secret_key = "sk_test_mock_secret_key"
    service.config.webhook_secret = "whsec_mock_webhook_secret"
    service.config.prices = {
        "pro_month": "price_pro_monthly_id",
        "pro_year": "price_pro_yearly_id",
        "business_month": "price_biz_monthly_id",
        "business_year": "price_biz_yearly_id",
    }
    service.config.price_to_plan = {
        "price_pro_monthly_id": "pro",
        "price_pro_yearly_id": "pro",
        "price_biz_monthly_id": "business",
        "price_biz_yearly_id": "business",
    }
    return service


# =====================================================================
# 1. Checkout Session Creation & Protection
# =====================================================================

@pytest.mark.asyncio
async def test_checkout_session_not_configured_raises_503(stripe_service, mock_user):
    stripe_service.config.secret_key = None
    with pytest.raises(HTTPException) as exc_info:
        await stripe_service.create_checkout_session(
            user=mock_user,
            plan_id="pro",
            billing_cycle="month",
            success_url="https://app.brevio.ai/success",
            cancel_url="https://app.brevio.ai/cancel",
        )
    assert exc_info.value.status_code == 503
    assert "not configured" in exc_info.value.detail


@pytest.mark.asyncio
async def test_checkout_session_active_subscription_raises_400(
    stripe_service, mock_user
):
    mock_user.plan_id = "pro"
    mock_user.stripe_subscription_status = "active"

    with pytest.raises(HTTPException) as exc_info:
        await stripe_service.create_checkout_session(
            user=mock_user,
            plan_id="business",
            billing_cycle="month",
            success_url="https://app.brevio.ai/success",
            cancel_url="https://app.brevio.ai/cancel",
        )
    assert exc_info.value.status_code == 400
    assert "already has an active subscription" in exc_info.value.detail


@pytest.mark.asyncio
async def test_checkout_session_creates_customer_and_session(
    stripe_service, mock_user
):
    mock_customer = MagicMock(id="cus_new_123")
    mock_session = MagicMock(url="https://checkout.stripe.com/pay/cs_test_abc")

    with patch("stripe.Customer.create", return_value=mock_customer) as mock_c_create, patch(
        "stripe.checkout.Session.create", return_value=mock_session
    ) as mock_s_create:
        url = await stripe_service.create_checkout_session(
            user=mock_user,
            plan_id="pro",
            billing_cycle="month",
            success_url="https://app.brevio.ai/success",
            cancel_url="https://app.brevio.ai/cancel",
        )

    assert url == "https://checkout.stripe.com/pay/cs_test_abc"
    mock_c_create.assert_called_once_with(
        email=mock_user.email,
        name=mock_user.username,
        metadata={"user_id": str(mock_user.id)},
    )
    stripe_service.user_service.user_repo.update_user.assert_awaited_with(
        mock_user.id, {"stripe_customer_id": "cus_new_123"}
    )
    mock_s_create.assert_called_once()
    kwargs = mock_s_create.call_args.kwargs
    assert kwargs["customer"] == "cus_new_123"
    assert kwargs["line_items"] == [{"price": "price_pro_monthly_id", "quantity": 1}]
    assert kwargs["mode"] == "subscription"


# =====================================================================
# 2. Customer Portal Session
# =====================================================================

@pytest.mark.asyncio
async def test_portal_session_requires_customer_id(stripe_service, mock_user):
    mock_user.stripe_customer_id = None
    with pytest.raises(HTTPException) as exc_info:
        await stripe_service.create_portal_session(
            user=mock_user, return_url="https://app.brevio.ai/billing"
        )
    assert exc_info.value.status_code == 400
    assert "No active billing account" in exc_info.value.detail


@pytest.mark.asyncio
async def test_portal_session_creates_portal_url(stripe_service, mock_user):
    mock_user.stripe_customer_id = "cus_existing_456"
    mock_portal = MagicMock(url="https://billing.stripe.com/p/session/test")

    with patch("stripe.billing_portal.Session.create", return_value=mock_portal):
        url = await stripe_service.create_portal_session(
            user=mock_user, return_url="https://app.brevio.ai/billing"
        )
    assert url == "https://billing.stripe.com/p/session/test"


# =====================================================================
# 3. Webhook Signature & Idempotency
# =====================================================================

@pytest.mark.asyncio
async def test_webhook_invalid_signature_raises_400(stripe_service):
    payload = b'{"id": "evt_test", "type": "checkout.session.completed"}'
    with patch(
        "stripe.Webhook.construct_event",
        side_effect=stripe.error.SignatureVerificationError("bad sig", "sig_header"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await stripe_service.handle_webhook(payload, "invalid_sig")
        assert exc_info.value.status_code == 400
        assert "Invalid signature" in exc_info.value.detail


@pytest.mark.asyncio
async def test_webhook_checkout_completed_applies_plan_and_credits(
    stripe_service, mock_user
):
    event_payload = {
        "id": "evt_checkout_100",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_100",
                "customer": "cus_test_100",
                "subscription": "sub_test_100",
                "invoice": "in_test_100",
                "metadata": {"user_id": str(mock_user.id), "plan_id": "pro"},
                "client_reference_id": str(mock_user.id),
            }
        },
    }
    raw_bytes = json.dumps(event_payload).encode("utf-8")

    with patch("stripe.Webhook.construct_event", return_value=event_payload):
        await stripe_service.handle_webhook(raw_bytes, "valid_sig")

    # Plan applied
    update_calls = stripe_service.user_service.user_repo.update_user.await_args_list
    assert any(
        call.args[1].get("plan_id") == "pro" and call.args[1].get("stripe_subscription_status") == "active"
        for call in update_calls
    )
    # Credits granted
    stripe_service.credit_service.grant_subscription_credits.assert_awaited_once_with(
        str(mock_user.id), 4000, "in_test_100", rollover_max=8000
    )


@pytest.mark.asyncio
async def test_webhook_duplicate_event_is_idempotent(stripe_service, mock_user):
    event_payload = {
        "id": "evt_duplicate_200",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_200",
                "customer": "cus_test_200",
                "subscription": "sub_test_200",
                "invoice": "in_test_200",
                "metadata": {"user_id": str(mock_user.id), "plan_id": "pro"},
            }
        },
    }
    raw_bytes = json.dumps(event_payload).encode("utf-8")

    with patch("stripe.Webhook.construct_event", return_value=event_payload):
        # First call processes event
        await stripe_service.handle_webhook(raw_bytes, "valid_sig")
        assert stripe_service.credit_service.grant_subscription_credits.await_count == 1

        # Second call with identical event_id must be skipped
        await stripe_service.handle_webhook(raw_bytes, "valid_sig")
        assert stripe_service.credit_service.grant_subscription_credits.await_count == 1


# =====================================================================
# 4. Lifecycle: Renewals, Cancellations, Payment Failures & Refunds
# =====================================================================

@pytest.mark.asyncio
async def test_webhook_subscription_updated_renewal(stripe_service, mock_user):
    event_payload = {
        "id": "evt_sub_update_300",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_active_300",
                "customer": "cus_test_100",
                "status": "active",
                "metadata": {"plan_id": "pro"},
                "items": {"data": [{"price": {"id": "price_pro_monthly_id"}}]},
            }
        },
    }
    raw_bytes = json.dumps(event_payload).encode("utf-8")

    with patch("stripe.Webhook.construct_event", return_value=event_payload):
        await stripe_service.handle_webhook(raw_bytes, "valid_sig")

    update_calls = stripe_service.user_service.user_repo.update_user.await_args_list
    assert any(
        call.args[1].get("plan_id") == "pro" and call.args[1].get("stripe_subscription_status") == "active"
        for call in update_calls
    )


@pytest.mark.asyncio
async def test_webhook_subscription_deleted_reverts_to_free(stripe_service, mock_user):
    mock_user.plan_id = "pro"
    mock_user.stripe_subscription_status = "active"

    event_payload = {
        "id": "evt_sub_del_400",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_canceled_400",
                "customer": "cus_test_100",
                "status": "canceled",
            }
        },
    }
    raw_bytes = json.dumps(event_payload).encode("utf-8")

    with patch("stripe.Webhook.construct_event", return_value=event_payload):
        await stripe_service.handle_webhook(raw_bytes, "valid_sig")

    update_calls = stripe_service.user_service.user_repo.update_user.await_args_list
    assert any(
        call.args[1].get("plan_id") == "free" and call.args[1].get("stripe_subscription_status") == "canceled"
        for call in update_calls
    )


@pytest.mark.asyncio
async def test_webhook_out_of_order_active_event_after_deletion_is_ignored(stripe_service, mock_user):
    """If subscription was already marked canceled, a delayed 'active' event must NOT restore it."""
    mock_user.stripe_subscription_id = "sub_canceled_123"
    mock_user.stripe_subscription_status = "canceled"
    mock_user.plan_id = "free"

    delayed_active_payload = {
        "id": "evt_delayed_sub_active",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_canceled_123",
                "customer": "cus_test_100",
                "status": "active",
                "metadata": {"plan_id": "pro"},
            }
        },
    }
    raw_bytes = json.dumps(delayed_active_payload).encode("utf-8")

    with patch("stripe.Webhook.construct_event", return_value=delayed_active_payload):
        await stripe_service.handle_webhook(raw_bytes, "valid_sig")

    # update_user should NOT have been called with plan_id="pro" or status="active"
    update_calls = stripe_service.user_service.user_repo.update_user.await_args_list
    assert not any(call.args[1].get("plan_id") == "pro" for call in update_calls)


@pytest.mark.asyncio
async def test_webhook_invoice_payment_failed_marks_past_due(stripe_service, mock_user):
    mock_user.plan_id = "pro"
    mock_user.stripe_subscription_status = "active"

    event_payload = {
        "id": "evt_inv_fail_500",
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "id": "in_failed_500",
                "customer": "cus_test_100",
                "status": "open",
            }
        },
    }
    raw_bytes = json.dumps(event_payload).encode("utf-8")

    with patch("stripe.Webhook.construct_event", return_value=event_payload):
        await stripe_service.handle_webhook(raw_bytes, "valid_sig")

    update_calls = stripe_service.user_service.user_repo.update_user.await_args_list
    assert any(
        call.args[1].get("stripe_subscription_status") == "past_due"
        for call in update_calls
    )


@pytest.mark.asyncio
async def test_webhook_charge_refunded_handles_cleanly(stripe_service):
    event_payload = {
        "id": "evt_refund_600",
        "type": "charge.refunded",
        "data": {
            "object": {
                "id": "ch_refund_600",
                "customer": "cus_test_100",
                "amount_refunded": 999,
            }
        },
    }
    raw_bytes = json.dumps(event_payload).encode("utf-8")

    with patch("stripe.Webhook.construct_event", return_value=event_payload):
        # Should execute cleanly without error and record processed
        await stripe_service.handle_webhook(raw_bytes, "valid_sig")

    event_doc = await stripe_service.stripe_event_repo.get_by_event_id("evt_refund_600")
    assert event_doc is not None
    assert event_doc.status == "processed"


# =====================================================================
# 5. Post-Checkout Sync Endpoint
# =====================================================================

@pytest.mark.asyncio
async def test_sync_user_subscription_with_session_id(stripe_service, mock_user):
    mock_session = {
        "id": "cs_test_sync_700",
        "customer": "cus_test_100",
        "subscription": "sub_test_700",
        "invoice": "in_test_700",
        "client_reference_id": str(mock_user.id),
        "metadata": {"user_id": str(mock_user.id), "plan_id": "pro"},
    }

    with patch("stripe.checkout.Session.retrieve", return_value=mock_session):
        res = await stripe_service.sync_user_subscription(
            mock_user, session_id="cs_test_sync_700"
        )

    assert res["synced"] is True
    assert res["via"] == "checkout_session"
    assert res["credits_balance"] == 4000
