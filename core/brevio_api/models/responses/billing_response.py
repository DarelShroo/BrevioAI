from typing import Dict, List, Optional

from pydantic import BaseModel


class ChunkTokenDetail(BaseModel):
    chunk_index: int
    system_prompt_tokens: int
    message_structure_tokens: int
    input_text_tokens: int
    expected_output_tokens: int
    total_input_tokens: int
    total_output_tokens: int
    chunk_cost: float


class BillingEstimateResponse(BaseModel):
    estimated_cost: float
    input_tokens: int = 0
    output_tokens: int = 0


class BillingTokenResponse(BaseModel):
    estimated_cost: float
    total_input_tokens: int
    total_output_tokens: int
    number_of_chunks: int
    system_prompt_tokens_per_chunk: int
    message_structure_tokens_per_chunk: int
    token_breakdown: Dict[str, int]
    chunks: Optional[List[ChunkTokenDetail]] = None
    has_postprocessing: bool = False
    postprocessing_tokens: Optional[int] = None
    postprocessing_cost: Optional[float] = None
