import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from bson import ObjectId
from mongomock_motor import AsyncMongoMockClient

from core.brevio_api.models.user.user_model import User
from core.brevio_api.services.billing.stripe_service import StripeService, StripeConfig
from core.brevio_api.services.billing.credit_service import CreditService
from core.brevio_api.repositories.billing.stripe_event_repository import StripeEventRepository
from core.brevio_api.repositories.user_repository import UserRepository
from core.brevio_api.services.user_service import UserService
from core.brevio_api.repositories.folder_entry_repository import FolderEntryRepository
from core.brevio_api.models.billing.credit_models import LedgerReason

@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client.get_database("test_stripe_integration")

@pytest.fixture
def mock_config():
    with patch("core.brevio_api.services.billing.stripe_service.StripeConfig") as mock:
        config_inst = mock.return_value
        config_inst.secret_key = "sk_test_123"
        config_inst.webhook_secret = "whsec_123"
        config_inst.prices = {
            "pro_month": "price_pro_123"
        }
        config_inst.get_plan_id_by_price_id.return_value = "pro"
        yield config_inst

@pytest.fixture
def user_id():
    return ObjectId()

@pytest_asyncio.fixture
async def setup_services(db, user_id, mock_config):
    user_repo = UserRepository(db["users"])
    folder_repo = FolderEntryRepository(db["folder_entries"])
    user_service = UserService(user_repo, folder_repo)
    stripe_event_repo = StripeEventRepository(db["stripe_webhook_events"])
    credit_service = CreditService.from_db(db, user_repo=user_repo)
    
    stripe_service = StripeService(user_service, stripe_event_repo, credit_service)
    stripe_service.config = mock_config
    
    await credit_service.ensure_indexes()
    
    # Create test user
    user = User(
        _id=user_id,
        username="testuser",
        email="test@example.com",
        password="hashed",
        stripe_customer_id="cus_123"
    )
    await db["users"].insert_one(user.model_dump(by_alias=True))
    
    return stripe_service, credit_service, user_service

@pytest.mark.asyncio
async def test_invoice_paid_grants_credits_idempotently(setup_services, user_id):
    stripe_service, credit_service, user_service = setup_services
    
    invoice_data = {
        "id": "in_123",
        "customer": "cus_123",
        "subscription": "sub_123",
        "lines": {
            "data": [
                {
                    "price": {"id": "price_pro_123"}
                }
            ]
        }
    }
    
    with patch("core.brevio_api.services.billing.plan_registry.get_plan") as mock_get_plan:
        mock_plan = MagicMock()
        mock_plan.plan_id = "pro"
        mock_plan.version = "1"
        mock_plan.credits_per_period = 4000
        mock_plan.rollover_max = 8000
        mock_get_plan.return_value = mock_plan
        
        # First webhook event
        await stripe_service._handle_invoice_paid(invoice_data)
        
        # Check credits were granted
        balance = await credit_service.get_balance(str(user_id))
        assert balance == 4000

        user = await user_service.get_user_by_id(str(user_id))
        assert user.plan_id == "pro"
        assert user.stripe_subscription_status == "active"
        
        # Verify ledger entry
        ledger_entries = await credit_service.ledger.collection.count_documents(
            {"user_id": user_id, "reason": LedgerReason.PERIOD_GRANT.value}
        )
        assert ledger_entries == 1
        
        # Second webhook event (duplicate)
        await stripe_service._handle_invoice_paid(invoice_data)
        
        # Balance should still be 4000
        balance = await credit_service.get_balance(str(user_id))
        assert balance == 4000
        
        # Still only one ledger entry
        ledger_entries = await credit_service.ledger.collection.count_documents(
            {"user_id": user_id, "reason": LedgerReason.PERIOD_GRANT.value}
        )
        assert ledger_entries == 1


@pytest.mark.asyncio
async def test_checkout_completed_applies_plan_and_credits(setup_services, user_id):
    stripe_service, credit_service, user_service = setup_services

    session = {
        "id": "cs_test_1",
        "client_reference_id": str(user_id),
        "customer": "cus_123",
        "subscription": "sub_checkout",
        "invoice": "in_checkout_1",
        "metadata": {"user_id": str(user_id), "plan_id": "pro"},
    }

    with patch("core.brevio_api.services.billing.plan_registry.get_plan") as mock_get_plan:
        mock_plan = MagicMock()
        mock_plan.plan_id = "pro"
        mock_plan.version = "1"
        mock_plan.credits_per_period = 4000
        mock_plan.rollover_max = 8000
        mock_get_plan.return_value = mock_plan

        await stripe_service._handle_checkout_completed(session)

    user = await user_service.get_user_by_id(str(user_id))
    assert user.plan_id == "pro"
    assert user.stripe_subscription_id == "sub_checkout"
    assert user.stripe_subscription_status == "active"
    balance = await credit_service.get_balance(str(user_id))
    assert balance == 4000


@pytest.mark.asyncio
async def test_sync_user_subscription_via_checkout_session(setup_services, user_id):
    stripe_service, credit_service, user_service = setup_services
    user = await user_service.get_user_by_id(str(user_id))

    session = {
        "id": "cs_test_sync",
        "client_reference_id": str(user_id),
        "customer": "cus_123",
        "subscription": "sub_sync",
        "invoice": "in_sync_1",
        "metadata": {"user_id": str(user_id), "plan_id": "business"},
    }

    with patch("core.brevio_api.services.billing.plan_registry.get_plan") as mock_get_plan, \
         patch("stripe.checkout.Session.retrieve", return_value=session):
        mock_plan = MagicMock()
        mock_plan.plan_id = "business"
        mock_plan.version = "1"
        mock_plan.credits_per_period = 20000
        mock_plan.rollover_max = 40000
        mock_get_plan.return_value = mock_plan

        result = await stripe_service.sync_user_subscription(user, session_id="cs_test_sync")

    assert result["synced"] is True
    assert result["plan_id"] == "business"
    assert result["credits_balance"] == 20000
    user = await user_service.get_user_by_id(str(user_id))
    assert user.plan_id == "business"

@pytest.mark.asyncio
async def test_invoice_paid_skips_non_subscription(setup_services, user_id):
    stripe_service, credit_service, _ = setup_services
    
    invoice_data = {
        "id": "in_456",
        "customer": "cus_123",
        "subscription": None,  # Not a subscription invoice
    }
    
    await stripe_service._handle_invoice_paid(invoice_data)
    balance = await credit_service.get_balance(str(user_id))
    assert balance == 0

@pytest.mark.asyncio
async def test_as_dict_supports_stripe_to_dict():
    from core.brevio_api.services.billing.stripe_service import _as_dict

    class FakeStripeObj:
        def to_dict(self):
            return {"id": "sub_x", "status": "active", "items": {"data": []}}

    assert _as_dict(FakeStripeObj())["id"] == "sub_x"
    assert _as_dict({"id": "sub_y"})["id"] == "sub_y"
    assert _as_dict(None) == {}


@pytest.mark.asyncio
async def test_invoice_payment_failed(setup_services, user_id, caplog):
    stripe_service, credit_service, _ = setup_services

    import json

    payload = json.dumps({
        "id": "evt_fail",
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "id": "in_fail",
                "customer": "cus_123"
            }
        }
    }).encode('utf-8')

    with patch("stripe.Webhook.construct_event") as mock_construct:
        mock_construct.return_value = json.loads(payload)

        await stripe_service.handle_webhook(payload, "sig")

        assert "Payment failed for invoice in_fail" in caplog.text

        balance = await credit_service.get_balance(str(user_id))
        assert balance == 0
