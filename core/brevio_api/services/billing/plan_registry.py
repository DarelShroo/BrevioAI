"""Load versioned commercial plans (FASE 5)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_PATH = (
    Path(__file__).resolve().parents[3] / "brevio" / "config" / "commercial_plans.yaml"
)

# Defaults match Free plan commercial contract (commercial_plans.yaml).
_FREE_BYTES_DOCUMENT = 25 * 1024 * 1024
_FREE_BYTES_AUDIO = 50 * 1024 * 1024
_FREE_BYTES_VIDEO = 250 * 1024 * 1024
_FREE_BYTES_PERIOD = 10 * _FREE_BYTES_VIDEO


@dataclass(frozen=True)
class PlanDefinition:
    plan_id: str
    name: str
    version: str
    status: str = "active"
    documents_per_period: int = 10
    pages_per_document: int = 200
    pages_per_period: int = 1000
    bytes_per_document: int = _FREE_BYTES_DOCUMENT
    bytes_per_audio: int = _FREE_BYTES_AUDIO
    bytes_per_video: int = _FREE_BYTES_VIDEO
    bytes_per_period: int = _FREE_BYTES_PERIOD
    credits_per_period: int = 100
    rollover_max: int = 200
    max_concurrent_jobs: int = 5
    scheduler_weight: int = 1
    scheduler_priority: int = 10
    byok_allowed: bool = True
    brevio_funded_models: tuple[str, ...] = field(default_factory=tuple)
    retention_days: int = 7
    media_enabled: bool = True
    youtube_enabled: bool = False
    list_price_monthly: Optional[float] = None
    cta_kind: str = "start_free"
    trial_days: Optional[int] = None

    @property
    def funds_all_models(self) -> bool:
        return len(self.brevio_funded_models) == 0

    def funds_model(self, model: str) -> bool:
        if self.funds_all_models:
            return True
        return model in self.brevio_funded_models

    def max_upload_bytes_for_source(self, source_type: str, filename: str = "") -> int:
        """Resolve commercial byte limit for a single file by source/extension."""
        lower = (filename or "").lower()
        if source_type == "media":
            video_ext = (".mp4", ".mov", ".mkv", ".webm", ".avi")
            audio_ext = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac")
            if lower.endswith(video_ext):
                return self.bytes_per_video
            if lower.endswith(audio_ext):
                return self.bytes_per_audio
            # Unknown media: apply the stricter of audio/video ceilings.
            return min(self.bytes_per_audio, self.bytes_per_video)
        return self.bytes_per_document


@dataclass(frozen=True)
class PricingDisplayConfig:
    currency: str
    show_billing_toggle: bool
    annual_discount_percent: int
    sales_email: str
    highlighted_plan_id: str


@dataclass(frozen=True)
class PlanRegistryConfig:
    period_mode: str
    rolling_days: int
    plan_change_usage_policy: str
    default_plan_id: str
    plans: dict[str, PlanDefinition]
    pricing: PricingDisplayConfig


def _optional_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    return float(value)


def _optional_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    return int(value)


def _parse_pricing(raw: dict[str, Any]) -> PricingDisplayConfig:
    block = raw.get("pricing") or {}
    return PricingDisplayConfig(
        currency=str(block.get("currency") or "EUR"),
        show_billing_toggle=bool(block.get("show_billing_toggle", False)),
        annual_discount_percent=max(0, int(block.get("annual_discount_percent") or 0)),
        sales_email=str(block.get("sales_email") or "support@brevio.com"),
        highlighted_plan_id=str(block.get("highlighted_plan_id") or "pro"),
    )


def _parse_plan(entry: dict[str, Any]) -> PlanDefinition:
    models = entry.get("brevio_funded_models") or []
    bytes_doc = int(entry.get("bytes_per_document", _FREE_BYTES_DOCUMENT))
    bytes_audio = int(entry.get("bytes_per_audio", _FREE_BYTES_AUDIO))
    bytes_video = int(entry.get("bytes_per_video", _FREE_BYTES_VIDEO))
    docs = int(entry.get("documents_per_period", 10))
    default_period_bytes = docs * max(bytes_doc, bytes_audio, bytes_video)
    return PlanDefinition(
        plan_id=str(entry["plan_id"]),
        name=str(entry.get("name") or entry["plan_id"]),
        version=str(entry.get("version") or "1"),
        status=str(entry.get("status") or "active"),
        documents_per_period=docs,
        pages_per_document=int(entry.get("pages_per_document", 200)),
        pages_per_period=int(entry.get("pages_per_period", 1000)),
        bytes_per_document=bytes_doc,
        bytes_per_audio=bytes_audio,
        bytes_per_video=bytes_video,
        bytes_per_period=int(entry.get("bytes_per_period", default_period_bytes)),
        credits_per_period=int(entry.get("credits_per_period", 100)),
        rollover_max=int(entry.get("rollover_max", 200)),
        max_concurrent_jobs=int(entry.get("max_concurrent_jobs", 5)),
        scheduler_weight=int(entry.get("scheduler_weight", 1)),
        scheduler_priority=int(entry.get("scheduler_priority", 10)),
        byok_allowed=bool(entry.get("byok_allowed", True)),
        brevio_funded_models=tuple(str(m) for m in models),
        retention_days=int(entry.get("retention_days", 7)),
        media_enabled=bool(entry.get("media_enabled", True)),
        youtube_enabled=bool(entry.get("youtube_enabled", False)),
        list_price_monthly=_optional_float(entry.get("list_price_monthly")),
        cta_kind=str(entry.get("cta_kind") or "start_free"),
        trial_days=_optional_int(entry.get("trial_days")),
    )


def load_plan_registry(path: Optional[str] = None) -> PlanRegistryConfig:
    resolved = Path(
        path
        or os.getenv("COMMERCIAL_PLANS_PATH")
        or str(_DEFAULT_PATH)
    )
    with resolved.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    plans = {}
    for entry in raw.get("plans") or []:
        plan = _parse_plan(entry)
        plans[plan.plan_id] = plan
    if not plans:
        raise ValueError(f"No plans defined in {resolved}")
    default_id = str(raw.get("default_plan_id") or "free")
    if default_id not in plans:
        default_id = next(iter(plans))
    pricing = _parse_pricing(raw)
    return PlanRegistryConfig(
        period_mode=str(raw.get("period_mode") or "calendar_month"),
        rolling_days=int(raw.get("rolling_days") or 30),
        plan_change_usage_policy=str(
            raw.get("plan_change_usage_policy") or "keep_period_counters"
        ),
        default_plan_id=default_id,
        plans=plans,
        pricing=pricing,
    )


@lru_cache(maxsize=1)
def get_plan_registry() -> PlanRegistryConfig:
    return load_plan_registry()


def clear_plan_registry_cache() -> None:
    get_plan_registry.cache_clear()


def get_plan(plan_id: str) -> PlanDefinition:
    registry = get_plan_registry()
    if plan_id not in registry.plans:
        raise KeyError(f"Unknown plan_id={plan_id}")
    return registry.plans[plan_id]


def default_plan() -> PlanDefinition:
    registry = get_plan_registry()
    return registry.plans[registry.default_plan_id]


def max_commercial_upload_bytes() -> int:
    """Largest single-file commercial limit across all plans (infra ceiling)."""
    registry = get_plan_registry()
    ceiling = 0
    for plan in registry.plans.values():
        ceiling = max(
            ceiling,
            plan.bytes_per_document,
            plan.bytes_per_audio,
            plan.bytes_per_video,
        )
    return max(ceiling, _FREE_BYTES_VIDEO)
