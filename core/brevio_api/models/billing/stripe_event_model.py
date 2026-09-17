"""Stripe Webhook Event model for idempotency (FASE 10, FASE 11)."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from bson import ObjectId
from pydantic import Field

from core.shared.models.user.base_model import BaseModel, SerializedObjectId


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StripeWebhookEvent(BaseModel):
    """
    Tracks Stripe webhook events to guarantee idempotency.
    Stripe guarantees at-least-once delivery, so we must deduplicate.
    """
    id: SerializedObjectId = Field(default_factory=ObjectId, alias="_id")
    event_id: str = Field(..., description="Stripe event.id (e.g., evt_123)")
    event_type: str = Field(..., description="Stripe event.type (e.g., checkout.session.completed)")
    status: str = Field(default="pending", description="pending | processed | failed")
    created_at: datetime = Field(default_factory=utcnow)
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict, description="Parsed (but unverified) or verified event data")
