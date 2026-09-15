import math
from dataclasses import dataclass

from core.shared.enums.model import ModelType
from core.shared.utils.model_tokens_utils import get_encoder


@dataclass(frozen=True)
class TokenCountResult:
    tokens: int
    method: str
    confidence: str
    estimated_error_margin: float


class TokenizerService:
    def count_tokens(self, text: str, model: ModelType) -> TokenCountResult:
        try:
            encoder = get_encoder(model)
            encoded = encoder.encode(text)
            return TokenCountResult(
                tokens=len(encoded),
                method="exact",
                confidence="high",
                estimated_error_margin=0.0,
            )
        except Exception:
            # Conservative deterministic fallback when tokenizer is not available.
            approx_tokens = max(1, math.ceil(len(text) / 4))
            return TokenCountResult(
                tokens=approx_tokens,
                method="approximation",
                confidence="medium",
                estimated_error_margin=0.10,
            )
