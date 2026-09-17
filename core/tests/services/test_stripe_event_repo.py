import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from core.brevio_api.repositories.billing.stripe_event_repository import StripeEventRepository
from core.brevio_api.models.billing.stripe_event_model import StripeWebhookEvent

@pytest.fixture
def mock_collection():
    return AsyncMock()

@pytest.fixture
def repo(mock_collection):
    return StripeEventRepository(mock_collection)

@pytest.mark.asyncio
async def test_mark_as_pending_new_event(repo, mock_collection):
    event = StripeWebhookEvent(event_id="evt_123", event_type="customer.subscription.updated", payload={})
    mock_collection.find_one_and_update.return_value = None
    
    result = await repo.mark_as_pending(event)
    
    assert result is True
    mock_collection.find_one_and_update.assert_called_once()
    mock_collection.update_one.assert_not_called()

@pytest.mark.asyncio
async def test_mark_as_pending_failed_event_retry(repo, mock_collection):
    event = StripeWebhookEvent(event_id="evt_123", event_type="customer.subscription.updated", payload={})
    # Mock that it previously failed
    mock_collection.find_one_and_update.return_value = {"status": "failed", "event_id": "evt_123"}
    
    result = await repo.mark_as_pending(event)
    
    assert result is True
    mock_collection.find_one_and_update.assert_called_once()
    mock_collection.update_one.assert_called_once()
    args, kwargs = mock_collection.update_one.call_args
    assert args[0] == {"event_id": "evt_123"}
    assert "$set" in args[1]
    assert args[1]["$set"]["status"] == "pending"

@pytest.mark.asyncio
async def test_mark_as_pending_already_processed(repo, mock_collection):
    event = StripeWebhookEvent(event_id="evt_123", event_type="customer.subscription.updated", payload={})
    # Mock that it is already processed
    mock_collection.find_one_and_update.return_value = {"status": "processed", "event_id": "evt_123"}
    
    result = await repo.mark_as_pending(event)
    
    assert result is False
    mock_collection.find_one_and_update.assert_called_once()
    mock_collection.update_one.assert_not_called()
