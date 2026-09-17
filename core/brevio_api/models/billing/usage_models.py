"""Usage and cost records for real provider consumption (FASE 4)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from bson import ObjectId
from pydantic import Field, field_validator

from core.shared.models.user.base_model import BaseModel, SerializedObjectId


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UsageSource(str, Enum):
    REAL = "REAL"
    ESTIMATED = "ESTIMATED"
    UNAVAILABLE = "UNAVAILABLE"


class UsageAttemptStatus(str, Enum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"


class UsageRecord(BaseModel):
    """One persisted provider attempt (including retries / fallbacks)."""

    id: SerializedObjectId = Field(default_factory=ObjectId, alias="_id")
    job_id: str
    user_id: SerializedObjectId
    attempt_id: str
    provider: str
    model: str
    credential_scope: str = "unknown"
    phase: str = ""
    status: str = UsageAttemptStatus.SUCCESS.value
    usage_source: str = UsageSource.UNAVAILABLE.value

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0
    audio_tokens: int = 0

    retry_index: int = 0
    is_retry: bool = False
    is_fallback: bool = False
    chunk_id: Optional[str] = None
    provider_request_id: Optional[str] = None
    finish_reason: Optional[str] = None
    error_type: Optional[str] = None

    started_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime = Field(default_factory=utcnow)
    created_at: datetime = Field(default_factory=utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "cached_input_tokens",
        "reasoning_tokens",
        "audio_tokens",
        "retry_index",
    )
    @classmethod
    def _non_neg_int(cls, value: int) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("token fields must be int")
        if value < 0:
            raise ValueError("token fields cannot be negative")
        return value


class CostRecord(BaseModel):
    """Commercial cost derived from a single UsageRecord (frozen pricing)."""

    id: SerializedObjectId = Field(default_factory=ObjectId, alias="_id")
    job_id: str
    usage_id: SerializedObjectId
    user_id: SerializedObjectId
    provider: str
    model: str

    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0

    input_unit_price: float = 0.0
    output_unit_price: float = 0.0
    cached_input_unit_price: float = 0.0

    provider_cost: float = 0.0
    platform_cost: float = 0.0
    currency: str = "USD"
    platform_currency: str = "EUR"
    credits: int = 0

    pricing_version: str = ""
    pricing_source: str = "pricing_registry"
    usage_source: str = UsageSource.UNAVAILABLE.value

    created_at: datetime = Field(default_factory=utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("input_tokens", "output_tokens", "cached_input_tokens", "credits")
    @classmethod
    def _non_neg(cls, value: int) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("must be int")
        if value < 0:
            raise ValueError("cannot be negative")
        return value
