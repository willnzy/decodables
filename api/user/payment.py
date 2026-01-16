"""
Payment API - Payment and checkout endpoints (v2).

@module api.user.payment
@version 2.4.0 (Container DI Migration)

Changes in v2.4.0:
- Container DI Migration
  - Migrated to Container-based dependency injection
  - Removed direct infrastructure.repositories imports
  - Removed get_async_db dependency from endpoints
  - User repository accessed via Container pattern
  - Architecture: API → Container → Service → Repository

Changes in v2.3.0:
- PAY-CRITICAL-1: Added dependency injection for PaymentService
- Migrated all endpoints to use Service layer with DI
- Architecture: API → Service (DI) → Stripe SDK (100% DDD)

Changes in v2.2.0:
- P-P0-1: Mark discount as used after checkout session created
- P-P0-2: Validate discount_percent range (1-100)
- P-HIGH-1: Extended plan_type validation (subscription + credits packages)
- P-HIGH-2: Verify discount target_plan matches requested plan
- P-MEDIUM-1: Added success logging for checkout
- P-MEDIUM-2: Validate stripe_customer_id format (cus_*)

Changes in v2.1.0:
- P-P0-2: Fixed sensitive info leakage in error messages
- Improved error handling to not expose Stripe internal errors

Endpoints:
- POST /api/v2/user/payment/checkout - Create checkout session
- POST /api/v2/user/payment/portal - Get billing portal URL
"""

import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from domains.identity.aggregates.user_profile import UserProfile
from dependencies import get_current_user
from infrastructure.rate_limiter import limiter
from container import get_container
from domains.billing.payment_service import PaymentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payment", tags=["user-payment-v2"])


# ==========================================
# Dependency Injection
# ==========================================

def get_payment_service() -> PaymentService:
    """Dependency injection factory for PaymentService."""
    return PaymentService()

# v2.2.0: Valid plan types - subscriptions and credit packages
VALID_PLAN_TYPES = {"t2", "t3", "credits_100", "credits_500", "credits_2000"}
PLAN_TYPE_PATTERN = "^(starter|pro|credits_100|credits_500|credits_2000)$"


# ==========================================
# Request/Response Models
# ==========================================

class CheckoutRequest(BaseModel):
    """Checkout request."""
    # v2.2.0: P-HIGH-1 - Extended plan_type validation
    plan_type: str = Field(..., pattern=PLAN_TYPE_PATTERN)


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
@limiter.limit("5/minute")  # v2.2.0: Added rate limiting
async def create_checkout(
    request: Request,
    req: CheckoutRequest,
    user: UserProfile = Depends(get_current_user),
    payment_service: PaymentService = Depends(get_payment_service),  # v2.3.0: DI
) -> CheckoutResponse:
    """
    Create a Stripe checkout session.

    Applies any available discount for the user.

    Args:
        req: Checkout request with plan_type (starter or pro)

    Returns:
        CheckoutResponse with checkout URL and discount info
    """
    try:
        # v2.4.0: Get user repository via Container (DI migration)
        container = get_container()
        user_repo = await container.get_user_repository()

        # v2.2.0: Get and validate discount
        discount = await user_repo.get_user_discount(user.user_id, req.plan_type)
        discount_percent = 0
        discount_id = None

        if discount:
            discount_percent = discount.get("discount_percent", 0)
            discount_id = discount.get("id")

            # v2.2.0: P-P0-2 - Validate discount_percent range
            if not (1 <= discount_percent <= 100):
                logger.warning(
                    f"Invalid discount_percent {discount_percent} for user {user['id']}, "
                    f"discount_id={discount_id}. Ignoring discount."
                )
                discount_percent = 0
                discount_id = None

            # v2.2.0: P-HIGH-2 - Verify discount target_plan matches requested plan
            target_plan = discount.get("target_plan")
            if target_plan and target_plan != req.plan_type:
                logger.warning(
                    f"Discount target_plan mismatch: discount for '{target_plan}' "
                    f"but requested '{req.plan_type}'. Ignoring discount."
                )
                discount_percent = 0
                discount_id = None

        # v2.3.0: Use PaymentService via DI
        url = payment_service.create_checkout_session(user.user_id, req.plan_type, discount_percent)

        if not url:
            raise HTTPException(500, "Failed to create checkout session")

        # v2.2.0: P-P0-1 - Mark discount as used AFTER successful checkout creation
        if discount_id and discount_percent > 0:
            await user_repo.mark_discount_used(discount_id)
            logger.info(
                f"Discount {discount_id} ({discount_percent}%) applied and marked used "
                f"for user {user['id']} on plan {req.plan_type}"
            )

        # v2.2.0: P-MEDIUM-1 - Log successful checkout
        logger.info(
            f"Checkout session created for user {user['id']}, "
            f"plan={req.plan_type}, discount={discount_percent}%"
        )

        return CheckoutResponse(
            url=url,
            discount_applied=discount_percent,
        )

    except HTTPException:
        raise
    except Exception as e:
        # v2.1.0: P-P0-2 fix - don't expose internal error details
        logger.error(f"Checkout error for user {user['id']}: {e}")
        raise HTTPException(500, "Failed to create checkout session. Please try again.")


@router.post("/portal", response_model=PortalResponse)
@limiter.limit("10/minute")  # v2.2.0: Added rate limiting
async def get_portal(
    request: Request,
    user: UserProfile = Depends(get_current_user),
    payment_service: PaymentService = Depends(get_payment_service),  # v2.3.0: DI
) -> PortalResponse:
    """
    Get Stripe billing portal URL.

    Allows users to manage their subscription.

    Returns:
        PortalResponse with portal URL
    """
    stripe_customer_id = user.get("stripe_customer_id")
    if not stripe_customer_id:
        raise HTTPException(400, "No subscription found")

    # v2.2.0: P-MEDIUM-2 - Validate stripe_customer_id format
    # Stripe customer IDs: cus_ followed by alphanumeric (including underscores in test mode)
    if not re.match(r"^cus_[a-zA-Z0-9_]+$", stripe_customer_id):
        logger.error(
            f"Invalid stripe_customer_id format for user {user['id']}: {stripe_customer_id}"
        )
        raise HTTPException(400, "Invalid customer data")

    try:
        # v2.3.0: Use PaymentService via DI
        url = payment_service.create_portal_session(user.user_id, stripe_customer_id)

        if not url:
            raise HTTPException(500, "Failed to create portal session")

        return PortalResponse(url=url)

    except HTTPException:
        raise
    except Exception as e:
        # v2.1.0: P-P0-2 fix - don't expose internal error details
        logger.error(f"Portal error for user {user['id']}: {e}")
        raise HTTPException(500, "Failed to access billing portal. Please try again.")
