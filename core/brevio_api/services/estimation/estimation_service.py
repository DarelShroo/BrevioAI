import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from math import ceil
from typing import List, Tuple

from core.brevio_api.models.brevio.document_processing_request import (
    DocumentProcessingRequest,
)
from core.brevio_api.services.estimation.document_extraction_service import (
    DocumentExtractionService,
    ExtractedDocument,
)
from core.brevio_api.services.estimation.prompt_estimation_service import (
    PromptEstimationService,
)
from core.brevio_api.services.estimation.tokenizer_service import TokenizerService
from core.shared.enums.model import ModelType
from core.shared.utils.context_validator import ContextValidator
from core.shared.utils.model_capabilities import get_model_capabilities
from core.shared.utils.output_token_policy import OutputTokenPolicy
from core.shared.utils.pricing_registry import (
    calculate_credits,
    calculate_provider_cost,
    convert_to_platform_currency,
    get_pricing_snapshot,
)


@dataclass(frozen=True)
class EstimationOutcome:
    request: DocumentProcessingRequest
    prompt_text: str
    prompt_template_tokens: int
    structural_tokens: int
    document_token_counts: List[Tuple[ExtractedDocument, int]]
    total_document_tokens: int
    total_input_tokens: int
    output_minimum_tokens: int
    output_expected_tokens: int
    output_max_tokens: int
    can_process: bool
    reason: str | None
    warnings: List[dict]
    chunking_required: bool
    chunking_calls: int
    provider_expected_cost: float
    provider_max_cost: float
    platform_expected_cost: float
    platform_max_cost: float
    expected_credits: int
    maximum_credits: int
    estimation_id: str
    estimated_at: str
    tokenization_method: str
    tokenization_confidence: str
    tokenization_error_margin: float


class EstimationService:
    def __init__(self) -> None:
        self._extraction_service = DocumentExtractionService()
        self._tokenizer = TokenizerService()
        self._context_validator = ContextValidator()
        self._output_policy = OutputTokenPolicy()
        self._prompt_estimation = PromptEstimationService()

    async def estimate(
        self,
        request: DocumentProcessingRequest,
        files_data: List[Tuple[str, bytes]],
    ) -> EstimationOutcome:
        extracted_documents = await self._extraction_service.extract_documents(
            files_data
        )
        prompt_text = await self._build_prompt(request)
        prompt_result = self._tokenizer.count_tokens(prompt_text, request.model)
        structural_text = self._prompt_estimation.structural_wrapper_text("")
        structural_result = self._tokenizer.count_tokens(structural_text, request.model)

        document_token_counts: List[Tuple[ExtractedDocument, int]] = []
        warnings: List[dict] = []
        total_document_tokens = 0
        total_prompt_tokens = 0
        total_structural_tokens = 0
        total_input_tokens = 0
        total_provider_expected_cost = 0.0
        total_provider_max_cost = 0.0
        total_platform_expected_cost = 0.0
        total_platform_max_cost = 0.0
        total_expected_credits = 0
        total_maximum_credits = 0
        total_chunking_calls = 0
        can_process = True
        reason: str | None = None
        tokenization_method = "exact"
        tokenization_confidence = "high"
        tokenization_error_margin = 0.0

        capabilities = get_model_capabilities(request.model)
        pricing_snapshot = get_pricing_snapshot(request.model)

        # We need to track the sum of min/expected/max for the final outcome
        total_minimum_tokens = 0
        total_expected_tokens = 0
        total_max_tokens = 0

        for document in extracted_documents:
            token_result = self._tokenizer.count_tokens(document.text, request.model)
            document_token_counts.append((document, token_result.tokens))
            total_document_tokens += token_result.tokens

            output_budget = self._output_policy.budget(
                request.model,
                request.summary_level,
                request.format,
                request.style,
                document_tokens=token_result.tokens,
                language=request.language,
            )
            total_minimum_tokens += output_budget.minimum
            total_expected_tokens += output_budget.expected
            total_max_tokens += output_budget.maximum

            if (
                prompt_result.method == "approximation"
                or token_result.method == "approximation"
            ):
                tokenization_method = "approximation"
                tokenization_confidence = "medium"
                tokenization_error_margin = max(
                    tokenization_error_margin,
                    prompt_result.estimated_error_margin,
                    token_result.estimated_error_margin,
                )

            if token_result.method == "approximation":
                warnings.append(
                    {
                        "code": "TOKENIZATION_APPROXIMATION",
                        "severity": "warning",
                        "message": (
                            f"Token count for {document.filename} was approximated with margin {token_result.estimated_error_margin:.2f}."
                        ),
                    }
                )

            if document.extraction_status == "empty":
                warnings.append(
                    {
                        "code": "EMPTY_DOCUMENT",
                        "severity": "warning",
                        "message": f"The document '{document.filename}' does not contain usable text.",
                    }
                )
            elif document.extraction_status == "ocr_required":
                warnings.append(
                    {
                        "code": "OCR_REQUIRED",
                        "severity": "warning",
                        "message": f"The document '{document.filename}' appears to be scanned and requires OCR.",
                    }
                )
            elif document.extraction_status == "partial":
                warnings.append(
                    {
                        "code": "PARTIAL_TEXT_EXTRACTION",
                        "severity": "warning",
                        "message": f"The document '{document.filename}' was only partially extracted.",
                    }
                )
            elif document.extraction_status == "unsupported":
                warnings.append(
                    {
                        "code": "UNSUPPORTED_FILE_TYPE",
                        "severity": "error",
                        "message": f"The document '{document.filename}' is not supported.",
                    }
                )
                can_process = False
                reason = "UNSUPPORTED_FILE_TYPE"
                continue

            input_tokens = (
                prompt_result.tokens + token_result.tokens + structural_result.tokens
            )
            context_result = self._context_validator.validate(
                input_tokens,
                output_budget,
                capabilities,
            )
            if (
                not context_result.can_process
                and context_result.reason == "MODEL_CONTEXT_EXCEEDED"
            ):
                can_process = False
                reason = context_result.reason

            chunking_calls = self._estimate_chunk_calls(
                input_tokens,
                capabilities.context_window,
                output_budget.maximum,
                capabilities.supports_chunking,
            )
            total_chunking_calls += chunking_calls
            prompt_tokens_total = prompt_result.tokens * chunking_calls
            structural_tokens_total = structural_result.tokens * chunking_calls
            document_total_input_tokens = (
                token_result.tokens + prompt_tokens_total + structural_tokens_total
            )
            total_prompt_tokens += prompt_tokens_total
            total_structural_tokens += structural_tokens_total
            total_input_tokens += document_total_input_tokens
            if chunking_calls > 1:
                warnings.append(
                    {
                        "code": "MODEL_REQUIRES_CHUNKING",
                        "severity": "warning",
                        "message": f"The document '{document.filename}' would require {chunking_calls} processing calls.",
                    }
                )

            provider_expected_cost, provider_max_cost = calculate_provider_cost(
                document_total_input_tokens,
                output_budget.expected * chunking_calls,
                output_budget.maximum * chunking_calls,
                pricing_snapshot,
            )
            total_provider_expected_cost += provider_expected_cost
            total_provider_max_cost += provider_max_cost

            platform_expected_cost = convert_to_platform_currency(
                provider_expected_cost, pricing_snapshot
            )
            platform_max_cost = convert_to_platform_currency(
                provider_max_cost, pricing_snapshot
            )
            total_platform_expected_cost += platform_expected_cost
            total_platform_max_cost += platform_max_cost
            total_expected_credits += calculate_credits(
                platform_expected_cost, pricing_snapshot
            )
            total_maximum_credits += calculate_credits(
                platform_max_cost, pricing_snapshot
            )

        if not can_process and reason is None:
            reason = "MODEL_CONTEXT_EXCEEDED"

        estimated_at = datetime.now(timezone.utc).isoformat()
        fingerprint = "|".join(
            [
                request.model.value,
                request.category,
                request.style,
                request.format.value,
                request.language.name,
                request.summary_level.value,
                str(len(extracted_documents)),
                str(total_document_tokens),
                str(total_input_tokens),
                str(total_chunking_calls),
            ]
        )
        estimation_id = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:24]

        return EstimationOutcome(
            request=request,
            prompt_text=prompt_text,
            prompt_template_tokens=total_prompt_tokens,
            structural_tokens=total_structural_tokens,
            document_token_counts=document_token_counts,
            total_document_tokens=total_document_tokens,
            total_input_tokens=total_input_tokens,
            output_minimum_tokens=total_minimum_tokens,
            output_expected_tokens=total_expected_tokens,
            output_max_tokens=total_max_tokens,
            can_process=can_process,
            reason=reason,
            warnings=warnings,
            chunking_required=total_chunking_calls > len(extracted_documents),
            chunking_calls=total_chunking_calls,
            provider_expected_cost=total_provider_expected_cost,
            provider_max_cost=total_provider_max_cost,
            platform_expected_cost=total_platform_expected_cost,
            platform_max_cost=total_platform_max_cost,
            expected_credits=total_expected_credits,
            maximum_credits=total_maximum_credits,
            estimation_id=estimation_id,
            estimated_at=estimated_at,
            tokenization_method=tokenization_method,
            tokenization_confidence=tokenization_confidence,
            tokenization_error_margin=tokenization_error_margin,
        )

    async def _build_prompt(self, request: DocumentProcessingRequest) -> str:
        return await self._prompt_estimation.build_prompt(
            category=request.category,
            style=request.style,
            output_format=request.format,
            language=request.language,
            summary_level=request.summary_level,
        )

    def _structural_wrapper_text(self) -> str:
        return "<document>\n{content}\n</document>"

    def _estimate_chunk_calls(
        self,
        total_input_tokens: int,
        context_window: int,
        max_output_tokens: int,
        supports_chunking: bool,
    ) -> int:
        required = total_input_tokens + max_output_tokens
        if required <= context_window:
            return 1
        if not supports_chunking:
            return 1
        usable_input = max(1, context_window - max_output_tokens)
        return max(1, (total_input_tokens + usable_input - 1) // usable_input)
