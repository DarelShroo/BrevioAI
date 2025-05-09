import asyncio
import logging
import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.source_type import SourceType
from core.brevio.enums.summary_level import SummaryLevel
from core.brevio.services.advanced_content_generator import AdvancedPromptGenerator
from core.brevio_api.dependencies.advanced_prompt_generator_dependency import (
    get_advanced_prompt_generator,
)
from core.brevio_api.dependencies.api_key_dependency import verify_api_key
from core.brevio_api.dependencies.billing_estimator_dependency import (
    get_billing_estimator,
)
from core.brevio_api.models.responses.billing_response import BillingEstimateResponse
from core.brevio_api.services.billing.billing_estimator_service import (
    BillingEstimatorService,
)
from core.shared.enums.model import ModelType
from core.shared.utils.model_tokens_utils import get_encoder

logger = logging.getLogger(__name__)


class BillingRoutes:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/billing", tags=["billing"])
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.get(
            "/estimate-media",
            response_model=BillingEstimateResponse,
            description="Estimate the cost of transcribing and summarizing a media file (in minutes)",
            status_code=status.HTTP_200_OK,
            responses={401: {"description": "Invalid API key"}},
        )
        async def estimate_billing_for_media(
            minutes: float = Query(
                ..., gt=0, description="Duration of the media in minutes"
            ),
            model: ModelType = Query(
                ModelType.GPT_4O_MINI,
                description="Model to use for the estimation",
            ),
            language: LanguageType = Query(
                LanguageType.ENGLISH,
                description="Language of the input text",
            ),
            verify_api_key: str = Depends(verify_api_key),
            billing_estimator: BillingEstimatorService = Depends(get_billing_estimator),
        ) -> None:
            # estimated_cost = billing_estimator.billing_for_media(minutes)
            # return BillingEstimateResponse(estimated_cost=estimated_cost)
            pass

        @self.router.get(
            "/estimate-documents",
            description="Estimate cost based on the number of tokens from frontend",
            status_code=status.HTTP_200_OK,
            responses={401: {"description": "Invalid API key"}},
        )
        async def estimate_billing_for_tokens(
            num_tokens_user: int = Query(
                ..., gt=0, description="Number of tokens from frontend"
            ),
            model: ModelType = Query(..., description="Model type"),
            language: LanguageType = Query(
                ..., description="Language of the input text"
            ),
            category: str = Query(..., description="Category of the input text"),
            style: str = Query(..., description="Style of the input text"),
            output_format: OutputFormatType = Query(
                ..., description="Output format of the input text"
            ),
            source_type: SourceType = Query(
                ..., description="Source type of the input text"
            ),
            summary_level: SummaryLevel = Query(
                ..., description="Summary level of the input text"
            ),
            verify_api_key: str = Depends(verify_api_key),
            billing_estimator: BillingEstimatorService = Depends(get_billing_estimator),
            acg: AdvancedPromptGenerator = Depends(get_advanced_prompt_generator),
        ) -> dict:
            try:
                billing_estimator.summary_tokens_predict(
                    num_tokens_user,
                    language_output=language,
                    summary_level=summary_level,
                )
                return {}
            except Exception as e:
                logger.error(f"Error estimating billing: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))


billing_router = BillingRoutes().router
