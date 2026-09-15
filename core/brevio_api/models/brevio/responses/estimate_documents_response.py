from typing import List, Optional

from pydantic import BaseModel, Field

from core.brevio_api.models.responses.base_response import BaseResponse


class EstimationWarning(BaseModel):
    code: str
    severity: str
    message: str


class DocumentExtractionMetadata(BaseModel):
    status: str
    pages_total: int = 0
    pages_with_text: int = 0
    pages_without_text: int = 0


class EstimatedDocument(BaseModel):
    filename: str
    tokens: int
    extraction: DocumentExtractionMetadata


class InputTokensEstimate(BaseModel):
    prompt_template: int
    documents_content: int
    structural: int
    total: int


class OutputTokensEstimate(BaseModel):
    minimum: int
    expected: int
    max_ceiling: int


class TokenizationMetadata(BaseModel):
    method: str
    confidence: str
    estimated_error_margin: float


class ModelEstimate(BaseModel):
    name: str
    provider: str
    access: str = "pay_per_use"
    requires_api_key: bool = True
    context_limit: int
    max_output_tokens: int
    supports_chunking: bool


class PricingEstimate(BaseModel):
    model: str
    provider_cost_currency: str
    platform_currency: str
    expected_cost: float
    max_cost: float
    pricing_version: str


class CreditsEstimate(BaseModel):
    expected: int
    maximum: int


class ChunkingEstimate(BaseModel):
    required: bool
    calls: int


class EstimationResult(BaseModel):
    input_tokens: InputTokensEstimate
    output_tokens: OutputTokensEstimate
    total_tokens_worst_case: int


class EstimateDocumentsData(BaseModel):
    can_process: bool
    reason: Optional[str] = None
    estimation: EstimationResult
    documents: List[EstimatedDocument]
    tokenization: TokenizationMetadata
    model: ModelEstimate
    pricing: PricingEstimate
    credits: CreditsEstimate
    chunking: ChunkingEstimate
    estimation_id: str
    estimated_at: str
    warnings: List[EstimationWarning] = Field(default_factory=list)


class EstimateDocumentsResponse(BaseResponse):
    data: EstimateDocumentsData
