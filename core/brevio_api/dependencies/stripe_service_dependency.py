from fastapi import Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from core.brevio_api.dependencies.db_dependency import get_db
from core.brevio_api.services.billing.stripe_service import StripeService

async def get_stripe_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> StripeService:
    return StripeService.from_db(db)
