from typing import TypedDict


class ModelPricing(TypedDict):
    input_cost_per_million: float
    output_cost_per_million: float
    postprocess_output_factor: float
    summary_output_factor: float
    media_cost_per_minute: float
    max_tokens_per_chunk: int
    chunk_overlap: int
    safe_percent: float
