"""
Payment Router - Payment and checkout endpoints

@module routers.payment
@version 3.24

Endpoints:
- POST /api/payment/checkout - Create checkout session
- POST /api/payment/portal - Get billing portal URL
"""

import logging

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from services.payment_service import (
    create_checkout_session,
    create_portal_session,
)
from services.db_service import get_user_discount
from services.rate_limiter import limiter
from dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payment", tags=["payment"])


# ==========================================
# Request Models
# ==========================================

class CheckoutRequest(BaseModel):
    plan_type: str  # "starter" | "pro"


# ==========================================
# Payment Endpoints
# ==========================================

@router.post("/checkout")
@limiter.limit("5/minute")  # Strict rate limit for payment APIs
def create_checkout(request: Request, req: CheckoutRequest, user: dict = Depends(get_current_user)):
    """
    Create a Stripe checkout session.
    
    Applies any available discount for the user.
    """
    try:
        # Apply discount if available
        discount = get_user_discount(user["id"], req.plan_type)
        discount_percent = discount.get("discount_percent", 0) if discount else 0
        
        url = create_checkout_session(user["id"], req.plan_type, discount_percent)
        return {"url": url, "discount_applied": discount_percent}
    except Exception as e:
        logger.error(f"Checkout error: {e}")
        raise HTTPException(500, f"Failed to create checkout: {str(e)}")


@router.post("/portal")
@limiter.limit("10/minute")  # Billing portal rate limit
def get_portal(request: Request, user: dict = Depends(get_current_user)):
    """Get Stripe billing portal URL."""
    stripe_customer_id = user.get("stripe_customer_id")
    if not stripe_customer_id:
        raise HTTPException(400, "No subscription found")
    
    try:
        url = create_portal_session(user["id"], stripe_customer_id)
        return {"url": url}
    except Exception as e:
        logger.error(f"Portal error: {e}")
        raise HTTPException(500, f"Failed to get portal: {str(e)}")
