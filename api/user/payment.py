"""
Payment API - Payment and checkout endpoints (v2).

@module api.user.payment
@version 2.0.0

Endpoints:
- POST /api/v2/user/payment/checkout - Create checkout session
- POST /api/v2/user/payment/portal - Get billing portal URL
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from dependencies import get_current_user
from infrastructure.rate_limiter import limiter
from infrastructure.repositories.user_repository import SupabaseUserRepository
from core.database import get_database_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payment", tags=["user-payment-v2"])


# ==========================================
# Request/Response Models
# ==========================================

class CheckoutRequest(BaseModel):
    """Checkout request."""
    plan_type: str = Field(..., pattern="^(starter|pro)$")


class CheckoutResponse(BaseModel):
    """Checkout response."""
    url: str
    discount_applied: int = 0


class PortalResponse(BaseModel):
    """Portal response."""
    url: str


# ==========================================
# Payment Endpoints
# ==========================================

@router.post("/checkout", response_model=CheckoutResponse)
@limiter.limit("5/minute")
async def create_checkout(
    request: Request,
    req: CheckoutRequest,
    user: dict = Depends(get_current_user),
) -> CheckoutResponse:
    """
    Create a Stripe checkout session.

    Applies any available discount for the user.

    Args:
        req: Checkout request with plan_type (starter or pro)

    Returns:
        CheckoutResponse with checkout URL and discount info
    """
    from domains.billing.payment_service import create_checkout_session

    try:
        # Apply discount if available
        user_repo = SupabaseUserRepository(get_database_client())
        discount = await user_repo.get_user_discount(user["id"], req.plan_type)
        discount_percent = discount.get("discount_percent", 0) if discount else 0

        url = create_checkout_session(user["id"], req.plan_type, discount_percent)

        if not url:
            raise HTTPException(500, "Failed to create checkout session")

        return CheckoutResponse(
            url=url,
            discount_applied=discount_percent,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Checkout error for user {user['id']}: {e}")
        raise HTTPException(500, f"Failed to create checkout: {str(e)}")


@router.post("/portal", response_model=PortalResponse)
@limiter.limit("10/minute")
async def get_portal(
    request: Request,
    user: dict = Depends(get_current_user),
) -> PortalResponse:
    """
    Get Stripe billing portal URL.

    Allows users to manage their subscription.

    Returns:
        PortalResponse with portal URL
    """
    from domains.billing.payment_service import create_portal_session

    stripe_customer_id = user.get("stripe_customer_id")
    if not stripe_customer_id:
        raise HTTPException(400, "No subscription found")

    try:
        url = create_portal_session(user["id"], stripe_customer_id)

        if not url:
            raise HTTPException(500, "Failed to create portal session")

        return PortalResponse(url=url)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Portal error for user {user['id']}: {e}")
        raise HTTPException(500, f"Failed to get portal: {str(e)}")
