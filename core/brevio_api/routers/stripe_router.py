from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.brevio_api.models.errors.api_codes import ApiErrorCode, CodedHTTPException
from core.brevio_api.dependencies.user_dependency import get_current_user
from core.brevio_api.dependencies.user_service_dependency import user_service_dependency
from core.brevio_api.dependencies.stripe_service_dependency import get_stripe_service
from core.brevio_api.models.user.user_model import User
from core.brevio_api.services.user_service import UserService
from core.brevio_api.services.billing.stripe_service import StripeService

router = APIRouter(prefix="/billing", tags=["Billing"])

class CheckoutRequest(BaseModel):
    plan_id: str
    billing_cycle: str
    success_url: str
    cancel_url: str

class PortalRequest(BaseModel):
    return_url: str


class SyncRequest(BaseModel):
    session_id: str | None = None

@router.post("/checkout")
async def create_checkout_session(
    request: CheckoutRequest,
    current_user_id: str = Depends(get_current_user),
    user_service: UserService = Depends(user_service_dependency),
    stripe_service: StripeService = Depends(get_stripe_service)
):
    try:
        user = await user_service.get_user_by_id(current_user_id)
        url = await stripe_service.create_checkout_session(
            user=user,
            plan_id=request.plan_id,
            billing_cycle=request.billing_cycle,
            success_url=request.success_url,
            cancel_url=request.cancel_url
        )
        return {"url": url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/portal")
async def create_portal_session(
    request: PortalRequest,
    current_user_id: str = Depends(get_current_user),
    user_service: UserService = Depends(user_service_dependency),
    stripe_service: StripeService = Depends(get_stripe_service)
):
    try:
        user = await user_service.get_user_by_id(current_user_id)
        url = await stripe_service.create_portal_session(
            user=user,
            return_url=request.return_url
        )
        return {"url": url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_service: StripeService = Depends(get_stripe_service)
):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not sig_header:
        raise CodedHTTPException(
            status_code=400,
            code=ApiErrorCode.MISSING_SIGNATURE,
        )
        
    try:
        await stripe_service.handle_webhook(payload, sig_header)
        return Response(status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_billing_status(
    current_user_id: str = Depends(get_current_user),
    user_service: UserService = Depends(user_service_dependency)
):
    """Returns safe billing status for the frontend (FASE 22)."""
    user = await user_service.get_user_by_id(current_user_id)
    return {
        "plan_id": user.plan_id,
        "stripe_subscription_status": user.stripe_subscription_status,
        "has_active_subscription": user.stripe_subscription_status in ["active", "trialing"] and user.plan_id != "free"
    }


@router.post("/sync")
async def sync_billing_state(
    request: SyncRequest = SyncRequest(),
    current_user_id: str = Depends(get_current_user),
    user_service: UserService = Depends(user_service_dependency),
    stripe_service: StripeService = Depends(get_stripe_service),
):
    """Pull Stripe subscription + latest paid invoice into local plan/credits.

    Called after Checkout return so plan/credits update even if webhooks lag.
    """
    user = await user_service.get_user_by_id(current_user_id)
    return await stripe_service.sync_user_subscription(
        user, session_id=request.session_id
    )
