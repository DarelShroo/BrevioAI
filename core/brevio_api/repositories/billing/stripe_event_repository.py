"""Repository for Stripe webhook events (FASE 10, 11)."""

from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import IndexModel, ASCENDING
from pymongo.errors import DuplicateKeyError

from core.brevio_api.models.billing.stripe_event_model import StripeWebhookEvent


class StripeEventRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    async def setup_indexes(self):
        """Create necessary indexes for idempotency and querying."""
        indexes = [
            IndexModel([("event_id", ASCENDING)], unique=True),
            IndexModel([("created_at", ASCENDING)]),
            IndexModel([("status", ASCENDING)]),
        ]
        await self.collection.create_indexes(indexes)

    async def get_by_event_id(self, event_id: str) -> Optional[StripeWebhookEvent]:
        doc = await self.collection.find_one({"event_id": event_id})
        if doc:
            return StripeWebhookEvent(**doc)
        return None

    async def mark_as_pending(self, event: StripeWebhookEvent) -> bool:
        """
        Attempts to insert the event as pending.
        Returns True if successful (this is the first time we see this event) or if it previously failed.
        Returns False if it is already processed or currently pending.
        """
        from pymongo import ReturnDocument
        
        doc = event.model_dump(by_alias=True)
        doc.pop("_id", None)  # Ensure no duplicate _id error on upsert
        
        # Use find_one_and_update with upsert
        # Return BEFORE so we can inspect the state *before* our update
        result = await self.collection.find_one_and_update(
            {"event_id": event.event_id},
            {"$setOnInsert": doc},
            upsert=True,
            return_document=ReturnDocument.BEFORE
        )
        
        if result is None:
            # It was inserted for the first time
            return True
            
        if result.get("status") == "failed":
            # It failed previously, let's reset to pending and allow retry
            await self.collection.update_one(
                {"event_id": event.event_id},
                {
                    "$set": {
                        "status": "pending",
                        "error_message": None,
                        "processed_at": None
                    }
                }
            )
            return True
            
        # If it's "processed" or "pending", we ignore it (idempotency)
        return False

    async def mark_as_processed(self, event_id: str) -> None:
        """Updates the status of an event to processed."""
        from core.brevio_api.models.billing.stripe_event_model import utcnow
        
        await self.collection.update_one(
            {"event_id": event_id},
            {
                "$set": {
                    "status": "processed",
                    "processed_at": utcnow()
                }
            }
        )

    async def mark_as_failed(self, event_id: str, error_message: str) -> None:
        """Updates the status of an event to failed with the given error message."""
        from core.brevio_api.models.billing.stripe_event_model import utcnow
        
        await self.collection.update_one(
            {"event_id": event_id},
            {
                "$set": {
                    "status": "failed",
                    "error_message": error_message,
                    "processed_at": utcnow()
                }
            }
        )
