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
        "media_cost_per_minute": 0.0,
    },
    ModelType.GPT_5_6.value: {
        "input_cost_per_million": 4.00,
        "output_cost_per_million": 20.00,
        "postprocess_output_factor": 0.5,
        "summary_output_factor": 0.9926,
        "media_cost_per_minute": 0.0,
    },
    ModelType.DEEPSEEK_V4_PRO.value: {
        "input_cost_per_million": 0.66,
        "output_cost_per_million": 1.98,
        "postprocess_output_factor": 0.5,
        "summary_output_factor": 0.9926,
        "media_cost_per_minute": 0.0,
    },
    ModelType.GROK_4_6.value: {
        "input_cost_per_million": 2.00,
        "output_cost_per_million": 6.00,
        "postprocess_output_factor": 0.5,
        "summary_output_factor": 0.9926,
        "media_cost_per_minute": 0.0,
    },
    ModelType.CLAUDE_SONNET_5.value: {
        "input_cost_per_million": 2.00,
        "output_cost_per_million": 10.00,
        "postprocess_output_factor": 0.5,
        "summary_output_factor": 0.9926,
        "media_cost_per_minute": 0.0,
    },
    ModelType.CLAUDE_HAIKU_4_5.value: {
        "input_cost_per_million": 1.00,
        "output_cost_per_million": 5.00,
        "postprocess_output_factor": 0.5,
        "summary_output_factor": 0.9926,
        "media_cost_per_minute": 0.0,
    },
    ModelType.DEEPSEEK_FLASH.value: {
        "input_cost_per_million": 0.15,
        "output_cost_per_million": 0.60,
        "postprocess_output_factor": 0.5,
        "summary_output_factor": 0.9926,
        "media_cost_per_minute": 0.0,
    },
    ModelType.GEMINI_3_1_FLASH_LITE.value: {
        "input_cost_per_million": 0.25,
        "output_cost_per_million": 1.50,
        "postprocess_output_factor": 0.5,
        "summary_output_factor": 0.9926,
        "media_cost_per_minute": 0.0,
    },
    ModelType.GPT_4.value: {
        "input_cost_per_million": 5.0,
        "output_cost_per_million": 15.0,
        "postprocess_output_factor": 0.5,
        "summary_output_factor": 0.9926,
        "media_cost_per_minute": 0.0,
    },
    ModelType.QWEN3_14B_BASE.value: {
        "input_cost_per_million": 0.0,
        "output_cost_per_million": 0.0,
        "postprocess_output_factor": 0.5,
        "summary_output_factor": 0.9926,
        "media_cost_per_minute": 0.0,
    },
    ModelType.QWEN3_14B.value: {
        "input_cost_per_million": 0.0,
        "output_cost_per_million": 0.0,
        "postprocess_output_factor": 0.5,
        "summary_output_factor": 0.9926,
        "media_cost_per_minute": 0.0,
    },
}
