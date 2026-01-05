"""
Payment Router - Payment and checkout endpoints

@module routers.payment
@version 3.24

Endpoints:
- POST /api/payment/checkout - Create checkout session
- POST /api/payment/portal - Get billing portal URL
"""

import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from services.payment_service import (
    create_checkout_session,
    get_billing_portal_url,
)
from dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payment", tags=["payment"])


# ==========================================
# Request Models
# ==========================================

class CheckoutRequest(BaseModel):
    plan: str  # "starter" | "pro"
    period: str = "monthly"  # "monthly" | "yearly"


class PortalRequest(BaseModel):
    return_url: str


# ==========================================
# Payment Endpoints
# ==========================================

@router.post("/checkout")
def create_checkout(req: CheckoutRequest, user: dict = Depends(get_current_user)):
    """Create a Stripe checkout session."""
    try:
        session_url = create_checkout_session(
            user_id=user["id"],
            plan=req.plan,
            period=req.period,
            email=user.get("email")
        )
        return {"checkout_url": session_url}
    except Exception as e:
        logger.error(f"Checkout error: {e}")
        raise HTTPException(500, f"Failed to create checkout: {str(e)}")


@router.post("/portal")
def get_portal(req: PortalRequest, user: dict = Depends(get_current_user)):
    """Get Stripe billing portal URL."""
    stripe_customer_id = user.get("stripe_customer_id")
    if not stripe_customer_id:
        raise HTTPException(400, "No billing account found")
    
    try:
        portal_url = get_billing_portal_url(stripe_customer_id, req.return_url)
        return {"portal_url": portal_url}
    except Exception as e:
        logger.error(f"Portal error: {e}")
        raise HTTPException(500, f"Failed to get portal: {str(e)}")
