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
- POST /api/v2/user/payment/upgrade - Upgrade subscription tier (WS6)
"""

import logging
import re
import stripe
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from domains.identity.aggregates.user_profile import UserProfile
from dependencies import get_current_user
from infrastructure.rate_limiter import limiter
from container import get_container
from domains.billing.payment_service import PaymentService
from domains.identity.constants import TIER_LEVELS

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
PLAN_TYPE_PATTERN = "^(t2|t3|credits_100|credits_500|credits_2000)$"


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


class UpgradeRequest(BaseModel):
    """Upgrade subscription request (WS6 #41)."""
    target_tier: str = Field(..., pattern="^(t2|t3)$")


class UpgradeResponse(BaseModel):
    """Upgrade subscription response."""
    status: str
    from_tier: str
    to_tier: str
    subscription_id: str
    message: str


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
        req: Checkout request with plan_type (t2, t3, or credits_*)

    Returns:
        CheckoutResponse with checkout URL and discount info
    """
    try:
        # v2.4.0: Get user repository via Container (DI migration)
        container = get_container()
        user_repo = await container.get_user_repository()

        # WS6 (#1): Get stripe_customer_id from user profile for customer binding
        user_profile = await user_repo.get_profile(user.user_id)
        stripe_customer_id = user_profile.get("stripe_customer_id") if user_profile else None

        # WS6 (#41): Upgrade interception — if user has active subscription and requests subscription plan
        is_subscription_plan = req.plan_type in ("t2", "t3")
        if is_subscription_plan and user_profile:
            current_tier = user_profile.get("tier", "t1")
            current_sub_status = user_profile.get("subscription_status")
            current_level = TIER_LEVELS.get(current_tier, 0)
            requested_level = TIER_LEVELS.get(req.plan_type, 0)

            if current_sub_status in ("active", "trialing"):
                if current_level == requested_level:
                    raise HTTPException(400, f"Already on {req.plan_type} plan")
                if current_level > requested_level:
                    raise HTTPException(400, "Use downgrade endpoint for lower tiers")
                # current_level < requested_level → upgrade: use /upgrade endpoint
                raise HTTPException(
                    400,
                    "You already have an active subscription. Use the upgrade endpoint to change your plan."
                )

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
                    f"Invalid discount_percent {discount_percent} for user {user.user_id}, "
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
        # WS6 (#1): Pass customer_id for Stripe Customer binding
        url = await payment_service.create_checkout_session(
            user.user_id, req.plan_type, discount_percent,
            customer_id=stripe_customer_id,
        )

        if not url:
            raise HTTPException(500, "Failed to create checkout session")

        # v2.2.0: P-P0-1 - Mark discount as used AFTER successful checkout creation
        if discount_id and discount_percent > 0:
            await user_repo.mark_discount_used(discount_id)
            logger.info(
                f"Discount {discount_id} ({discount_percent}%) applied and marked used "
                f"for user {user.user_id} on plan {req.plan_type}"
            )

        # v2.2.0: P-MEDIUM-1 - Log successful checkout
        logger.info(
            f"Checkout session created for user {user.user_id}, "
            f"plan={req.plan_type}, discount={discount_percent}%"
        )

        return CheckoutResponse(
            url=url,
            discount_applied=discount_percent,
        )

    except HTTPException:
        raise
    except stripe.error.IdempotencyError:
        # WS6 (#3): Return 409 instead of 500 for duplicate checkout requests
        logger.info(f"[Checkout] Duplicate request for {user.user_id}:{req.plan_type}")
        raise HTTPException(409, "Checkout session already created. Please wait.")
    except Exception as e:
        # v2.1.0: P-P0-2 fix - don't expose internal error details
        logger.error(f"Checkout error for user {user.user_id}: {e}")
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
    stripe_customer_id = user.stripe_customer_id
    if not stripe_customer_id:
        raise HTTPException(400, "No subscription found")

    # v2.2.0: P-MEDIUM-2 - Validate stripe_customer_id format
    # Stripe customer IDs: cus_ followed by alphanumeric (including underscores in test mode)
    if not re.match(r"^cus_[a-zA-Z0-9_]+$", stripe_customer_id):
        logger.error(
            f"Invalid stripe_customer_id format for user {user.user_id}: {stripe_customer_id}"
        )
        raise HTTPException(400, "Invalid customer data")

    try:
        # v2.3.0: Use PaymentService via DI
        url = await payment_service.create_portal_session(user.user_id, stripe_customer_id)

        if not url:
            raise HTTPException(500, "Failed to create portal session")

        return PortalResponse(url=url)

    except HTTPException:
        raise
    except Exception as e:
        # v2.1.0: P-P0-2 fix - don't expose internal error details
        logger.error(f"Portal error for user {user.user_id}: {e}")
        raise HTTPException(500, "Failed to access billing portal. Please try again.")


@router.post("/upgrade", response_model=UpgradeResponse)
@limiter.limit("3/minute")
async def upgrade_subscription(
    request: Request,
    req: UpgradeRequest,
    user: UserProfile = Depends(get_current_user),
) -> UpgradeResponse:
    """
    Upgrade subscription to a higher tier (WS6 #41).

    Uses Stripe Subscription.modify() with proration.
    Tier change in local DB is driven by customer.subscription.updated webhook.

    Args:
        req: UpgradeRequest with target_tier (t2 or t3)

    Returns:
        UpgradeResponse with upgrade status
    """
    from domains.subscriptions.exceptions import (
        UserNotFoundException,
        NoStripeCustomerException,
        NoActiveSubscriptionException,
        InvalidTierException,
        InvalidDowngradePathException,
        PriceIdNotConfiguredException,
        SubscriptionModifyFailedException,
    )

    try:
        container = get_container()
        subscription_service = await container.get_subscription_service()

        result = await subscription_service.upgrade_subscription(
            user_id=user.user_id,
            target_tier=req.target_tier,
        )

        return UpgradeResponse(
            status=result["status"],
            from_tier=result["from_tier"],
            to_tier=result["to_tier"],
            subscription_id=result["subscription_id"],
            message=result["message"],
        )

    except UserNotFoundException:
        raise HTTPException(404, "User not found")
    except NoStripeCustomerException:
        raise HTTPException(400, "No Stripe customer found. Please subscribe first.")
    except NoActiveSubscriptionException:
        raise HTTPException(400, "No active subscription to upgrade")
    except InvalidTierException as e:
        raise HTTPException(400, str(e))
    except InvalidDowngradePathException:
        raise HTTPException(400, "Target tier must be higher than current tier. Use downgrade endpoint for lower tiers.")
    except PriceIdNotConfiguredException as e:
        logger.error(f"[Upgrade] Price ID not configured: {e}")
        raise HTTPException(500, "Service configuration error. Please contact support.")
    except SubscriptionModifyFailedException:
        raise HTTPException(500, "Failed to modify subscription. Please try again.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Upgrade] Error for user {user.user_id}: {e}")
        raise HTTPException(500, "Failed to upgrade subscription. Please try again.")
