"""Commercial credit models (FASE 3). Integers only; Mongo is authority."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from bson import ObjectId
from pydantic import Field, field_validator

from core.shared.models.user.base_model import BaseModel, SerializedObjectId


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ReservationStatus(str, Enum):
    PENDING = "PENDING"
    COMMITTED = "COMMITTED"
    RELEASED = "RELEASED"


class SettlementStatus(str, Enum):
    PENDING = "PENDING"
    SETTLED = "SETTLED"


class BillingMode(str, Enum):
    """How inference is funded for a job.

    LOCAL: Ollama / no API key required — still reserves plan credits as quota.
    BYOK: user provider key for inference — plan credits still reserved/settled.
    PLATFORM: Brevio-funded inference — credits reserved/settled.
    """

    LOCAL = "LOCAL"
    BYOK = "BYOK"
    PLATFORM = "PLATFORM"


class LedgerReason(str, Enum):
    RESERVE = "RESERVE"
    RELEASE = "RELEASE"
    SETTLE_CONSUME = "SETTLE_CONSUME"
    COMPENSATE = "COMPENSATE"
    MIGRATE = "MIGRATE"
    SUBSCRIPTION_GRANT = "SUBSCRIPTION_GRANT"
    PERIOD_GRANT = "PERIOD_GRANT"


class CreditAccount(BaseModel):
    id: SerializedObjectId = Field(default_factory=ObjectId, alias="_id")
    user_id: SerializedObjectId
    balance: int = 0
    version: int = 1
    # Idempotency marker for monthly / Stripe period grants with rollover.
    last_period_grant_key: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    @field_validator("balance")
    @classmethod
    def _non_negative(cls, value: int) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("balance must be int")
        if value < 0:
            raise ValueError("balance cannot be negative")
        return value


class CreditReservation(BaseModel):
    id: SerializedObjectId = Field(default_factory=ObjectId, alias="_id")
    job_id: str
    user_id: SerializedObjectId
    account_id: SerializedObjectId
    amount: int
    expected_amount: int = 0
    billing_mode: str = BillingMode.PLATFORM.value
    status: str = ReservationStatus.PENDING.value
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime
    released_at: Optional[datetime] = None
    committed_at: Optional[datetime] = None

    @field_validator("amount", "expected_amount")
    @classmethod
    def _non_neg_amounts(cls, value: int) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("amount must be int")
        if value < 0:
            raise ValueError("amount cannot be negative")
        return value


class CreditLedgerEntry(BaseModel):
    id: SerializedObjectId = Field(default_factory=ObjectId, alias="_id")
    account_id: SerializedObjectId
    user_id: SerializedObjectId
    job_id: Optional[str] = None
    reservation_id: Optional[SerializedObjectId] = None
    settlement_id: Optional[SerializedObjectId] = None
    delta: int
    reason: str
    created_at: datetime = Field(default_factory=utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("delta")
    @classmethod
    def _delta_int(cls, value: int) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("delta must be int")
        return value


class JobSettlement(BaseModel):
    id: SerializedObjectId = Field(default_factory=ObjectId, alias="_id")
    job_id: str
    user_id: SerializedObjectId
    reservation_id: Optional[SerializedObjectId] = None
    billing_mode: str = BillingMode.PLATFORM.value
    reserved_credits: int = 0
    consumed_credits: int = 0
    released_credits: int = 0
    status: str = SettlementStatus.SETTLED.value
    overrun_detected: bool = False
    overrun_requested: int = 0
    created_at: datetime = Field(default_factory=utcnow)
    settled_at: datetime = Field(default_factory=utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("reserved_credits", "consumed_credits", "released_credits")
    @classmethod
    def _non_neg(cls, value: int) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("credits must be int")
        if value < 0:
            raise ValueError("credits cannot be negative")
        return value
