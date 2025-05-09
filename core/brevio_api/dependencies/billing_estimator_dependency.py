from fastapi import Query

from core.brevio.enums.language import LanguageType
from core.brevio_api.services.billing.billing_estimator_service import (
    BillingEstimatorService,
)
from core.shared.enums.model import ModelType


def get_billing_estimator() -> BillingEstimatorService:
    return BillingEstimatorService()
