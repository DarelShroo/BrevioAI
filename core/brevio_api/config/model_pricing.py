import os
from typing import Dict

from core.brevio_api.enums.model_pricing import ModelPricing
from core.shared.enums.model import ModelType

MODEL_TOKEN_PRICING: Dict[str, ModelPricing] = {
    ModelType.GPT_4O_MINI.value: {
        "input_cost_per_million": 0.15,
        "output_cost_per_million": 0.60,
        "postprocess_output_factor": 0.5,
        "summary_output_factor": 0.9926,
        "media_cost_per_minute": 0.10,
        "max_tokens_per_chunk": int(os.getenv("MAX_TOKENS_PER_CHUNK") or 3000),
        "chunk_overlap": 200,
        "safe_percent": 0.05,
    },
    ModelType.DEEPSEEK_CHAT.value: {
        "input_cost_per_million": 0.15,
        "output_cost_per_million": 0.60,
        "postprocess_output_factor": 0.5,
        "summary_output_factor": 0.9926,
        "media_cost_per_minute": 0.10,
        "max_tokens_per_chunk": int(os.getenv("MAX_TOKENS_PER_CHUNK") or 3000),
        "chunk_overlap": 200,
        "safe_percent": 0.05,
    },
}
