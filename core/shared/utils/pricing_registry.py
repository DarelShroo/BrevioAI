import os
from dataclasses import dataclass
from datetime import date
from math import ceil
from typing import Dict

from core.shared.enums.model import ModelType


@dataclass(frozen=True)
class PricingSnapshot:
    provider: str
    model: str
    input_price_per_million: float
    output_price_per_million: float
    cached_input_price_per_million: float
    currency: str
    effective_from: str
    pricing_version: str
    platform_currency: str
    fx_rate_to_platform: float
    commercial_margin: float
    credit_unit_value: float
    minimum_credits: int


def _commercial_fields(*, minimum_credits: int | None = None) -> dict:
    credits = (
        minimum_credits
        if minimum_credits is not None
        else int(os.getenv("MINIMUM_CREDITS", "1"))
    )
    return {
        "effective_from": os.getenv("PRICING_EFFECTIVE_FROM", date.today().isoformat()),
        "pricing_version": os.getenv("PRICING_VERSION", "2026-09-15"),
        "platform_currency": os.getenv("PLATFORM_CURRENCY", "EUR"),
        "fx_rate_to_platform": float(os.getenv("USD_TO_PLATFORM_RATE", "0.92")),
        "commercial_margin": float(os.getenv("COMMERCIAL_MARGIN", "0.18")),
        "credit_unit_value": float(os.getenv("CREDIT_UNIT_VALUE", "0.01")),
        "minimum_credits": credits,
    }


MODEL_PRICING_REGISTRY: Dict[ModelType, PricingSnapshot] = {
    ModelType.GPT_4O_MINI: PricingSnapshot(
        provider="openai",
        model=ModelType.GPT_4O_MINI.value,
        input_price_per_million=0.15,
        output_price_per_million=0.60,
        cached_input_price_per_million=0.075,
        currency="USD",
        **_commercial_fields(),
    ),
    ModelType.GPT_5_6: PricingSnapshot(
        provider="openai",
        model=ModelType.GPT_5_6.value,
        input_price_per_million=4.00,
        output_price_per_million=20.00,
        cached_input_price_per_million=0.40,
        currency="USD",
        **_commercial_fields(),
    ),
    ModelType.DEEPSEEK_V4_PRO: PricingSnapshot(
        provider="deepseek",
        model=ModelType.DEEPSEEK_V4_PRO.value,
        input_price_per_million=0.66,
        output_price_per_million=1.98,
        cached_input_price_per_million=0.022,
        currency="USD",
        **_commercial_fields(),
    ),
    ModelType.DEEPSEEK_FLASH: PricingSnapshot(
        provider="deepseek",
        model=ModelType.DEEPSEEK_FLASH.value,
        input_price_per_million=0.15,
        output_price_per_million=0.60,
        cached_input_price_per_million=0.003,
        currency="USD",
        **_commercial_fields(),
    ),
    ModelType.GEMINI_3_1_FLASH_LITE: PricingSnapshot(
        provider="google",
        model=ModelType.GEMINI_3_1_FLASH_LITE.value,
        input_price_per_million=0.25,
        output_price_per_million=1.50,
        cached_input_price_per_million=0.025,
        currency="USD",
        **_commercial_fields(),
    ),
    ModelType.GROK_4_6: PricingSnapshot(
        provider="xai",
        model=ModelType.GROK_4_6.value,
        input_price_per_million=2.00,
        output_price_per_million=6.00,
        cached_input_price_per_million=0.50,
        currency="USD",
        **_commercial_fields(),
    ),
    ModelType.CLAUDE_SONNET_5: PricingSnapshot(
        provider="anthropic",
        model=ModelType.CLAUDE_SONNET_5.value,
        input_price_per_million=2.00,
        output_price_per_million=10.00,
        cached_input_price_per_million=0.20,
        currency="USD",
        **_commercial_fields(),
    ),
    ModelType.CLAUDE_HAIKU_4_5: PricingSnapshot(
        provider="anthropic",
        model=ModelType.CLAUDE_HAIKU_4_5.value,
        input_price_per_million=1.00,
        output_price_per_million=5.00,
        cached_input_price_per_million=0.10,
        currency="USD",
        **_commercial_fields(),
    ),
    ModelType.DEEPSEEK_R1_LOCAL_IQ3_XS: PricingSnapshot(
        provider="ollama",
        model=ModelType.DEEPSEEK_R1_LOCAL_IQ3_XS.value,
        input_price_per_million=0.0,
        output_price_per_million=0.0,
        cached_input_price_per_million=0.0,
        currency="USD",
        **_commercial_fields(minimum_credits=1),
    ),
    ModelType.GPT_OSS_20B: PricingSnapshot(
        provider="ollama",
        model=ModelType.GPT_OSS_20B.value,
        input_price_per_million=0.0,
        output_price_per_million=0.0,
        cached_input_price_per_million=0.0,
        currency="USD",
        **_commercial_fields(minimum_credits=1),
    ),
    ModelType.GEMMA4_31B_IQ3: PricingSnapshot(
        provider="ollama",
        model=ModelType.GEMMA4_31B_IQ3.value,
        input_price_per_million=0.0,
        output_price_per_million=0.0,
        cached_input_price_per_million=0.0,
        currency="USD",
        **_commercial_fields(minimum_credits=1),
    ),
    ModelType.QWEN3_8B: PricingSnapshot(
        provider="ollama",
        model=ModelType.QWEN3_8B.value,
        input_price_per_million=0.0,
        output_price_per_million=0.0,
        cached_input_price_per_million=0.0,
        currency="USD",
        **_commercial_fields(minimum_credits=1),
    ),
    ModelType.QWEN3_14B_BASE: PricingSnapshot(
        provider="ollama",
        model=ModelType.QWEN3_14B_BASE.value,
        input_price_per_million=0.0,
        output_price_per_million=0.0,
        cached_input_price_per_million=0.0,
        currency="USD",
        **_commercial_fields(minimum_credits=1),
    ),
    ModelType.QWEN3_14B: PricingSnapshot(
        provider="ollama",
        model=ModelType.QWEN3_14B.value,
        input_price_per_million=0.0,
        output_price_per_million=0.0,
        cached_input_price_per_million=0.0,
        currency="USD",
        **_commercial_fields(minimum_credits=1),
    ),
    ModelType.QWEN3_32B: PricingSnapshot(
        provider="ollama",
        model=ModelType.QWEN3_32B.value,
        input_price_per_million=0.0,
        output_price_per_million=0.0,
        cached_input_price_per_million=0.0,
        currency="USD",
        **_commercial_fields(minimum_credits=1),
    ),
    ModelType.GPT_4: PricingSnapshot(
        provider="openai",
        model=ModelType.GPT_4.value,
        input_price_per_million=5.0,
        output_price_per_million=15.0,
        cached_input_price_per_million=2.5,
        currency="USD",
        **_commercial_fields(),
    ),
}


def get_pricing_snapshot(model: ModelType) -> PricingSnapshot:
    if model not in MODEL_PRICING_REGISTRY:
        raise ValueError(f"Pricing not configured for model '{model.value}'")
    return MODEL_PRICING_REGISTRY[model]


def calculate_provider_cost(
    input_tokens: int,
    expected_output_tokens: int,
    max_output_tokens: int,
    snapshot: PricingSnapshot,
) -> tuple[float, float]:
    expected_cost = (
        input_tokens * snapshot.input_price_per_million
        + expected_output_tokens * snapshot.output_price_per_million
    ) / 1_000_000
    max_cost = (
        input_tokens * snapshot.input_price_per_million
        + max_output_tokens * snapshot.output_price_per_million
    ) / 1_000_000
    return expected_cost, max_cost


def calculate_actual_provider_cost(
    *,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int,
    snapshot: PricingSnapshot,
) -> float:
    """Real usage cost. Cached tokens priced at cached_input rate when > 0."""
    cached = max(0, int(cached_input_tokens or 0))
    inp = max(0, int(input_tokens or 0))
    out = max(0, int(output_tokens or 0))
    billable_input = max(0, inp - cached)
    return (
        billable_input * snapshot.input_price_per_million
        + cached * snapshot.cached_input_price_per_million
        + out * snapshot.output_price_per_million
    ) / 1_000_000


def convert_to_platform_currency(cost: float, snapshot: PricingSnapshot) -> float:
    converted = cost * snapshot.fx_rate_to_platform
    return round(converted * (1 + snapshot.commercial_margin), 6)


def calculate_credits(cost: float, snapshot: PricingSnapshot) -> int:
    if snapshot.credit_unit_value <= 0:
        raise ValueError("credit_unit_value must be positive")
    # Zero-priced local models still burn the plan's minimum credit unit.
    if snapshot.input_price_per_million <= 0 and snapshot.output_price_per_million <= 0:
        return max(0, int(snapshot.minimum_credits))
    credits = ceil(cost / snapshot.credit_unit_value)
    return max(snapshot.minimum_credits, credits)
