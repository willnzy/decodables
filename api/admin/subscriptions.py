"""
Admin Subscriptions Router - Subscription management endpoints for admins

@module api.admin.subscriptions
@version 3.25

Changes:
- v3.25: Security improvements
  - SUB-MEDIUM-1: Added field length limits to request models
  - SUB-MEDIUM-2: Added target_tier enum validation
  - SUB-LOW-1: Limited Stripe error exposure

Endpoints:
- POST /api/admin/refund - Process refund
- POST /api/admin/subscription/cancel - Cancel subscription
- POST /api/admin/subscription/downgrade - Downgrade subscription
"""

import os
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field, field_validator

from core.database import get_database_client
from infrastructure.repositories import (
    SupabaseAdminUsersRepository,
    SupabasePaymentRepository,
    SupabaseUserRepository,
)
from domains.billing.payment_service import (
    get_customer_subscriptions,
    cancel_subscription,
    create_refund,
    get_payment_intent_details,
)
from infrastructure.rate_limiter import limiter
from dependencies import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["admin-subscriptions-v2"])


# ==========================================
# Constants (v3.25)
# ==========================================

# v3.25: SUB-MEDIUM-2 - Valid target tiers for downgrade
VALID_TARGET_TIERS = {"free", "starter"}

# v3.25: Monthly credits by tier (from CLAUDE.md business rules)
TIER_MONTHLY_CREDITS = {
    "free": 0,
    "starter": 200,
    "pro": 500,
}


# ==========================================
# Request Models (v3.25: Added field validation)
# ==========================================

class AdminRefundRequest(BaseModel):
    # v3.25: SUB-MEDIUM-1 - Field length limits
    user_id: str = Field(..., min_length=1, max_length=100)
    user_code: str = Field(..., min_length=1, max_length=50)  # Must match for verification
    payment_intent_id: str = Field(..., min_length=1, max_length=100)
    amount_cents: Optional[int] = Field(None, ge=1, le=100000000)  # None = full refund, max $1M
    reason: str = Field(..., min_length=1, max_length=1000)


class AdminCancelSubscriptionRequest(BaseModel):
    # v3.25: SUB-MEDIUM-1 - Field length limits
    user_id: str = Field(..., min_length=1, max_length=100)
    user_code: str = Field(..., min_length=1, max_length=50)  # Must match for verification
    subscription_id: str = Field(..., min_length=1, max_length=100)
    immediate: bool = False  # True = cancel now, False = cancel at period end
    reason: str = Field(..., min_length=1, max_length=1000)


class AdminDowngradeRequest(BaseModel):
    # v3.25: SUB-MEDIUM-1 - Field length limits
    user_id: str = Field(..., min_length=1, max_length=100)
    user_code: str = Field(..., min_length=1, max_length=50)  # For verification
    user_email: str = Field(..., min_length=1, max_length=255)  # For verification
    target_tier: str = Field(..., max_length=20)  # 'starter' | 'free'
    immediate: bool = False  # True = immediate, False = apply at period end
    reason: str = Field(..., min_length=1, max_length=1000)

    # v3.25: SUB-MEDIUM-2 - target_tier enum validation
    @field_validator("target_tier")
    @classmethod
    def validate_target_tier(cls, v: str) -> str:
        v_lower = v.lower()
        if v_lower not in VALID_TARGET_TIERS:
            raise ValueError(f"Invalid target_tier. Must be one of: {', '.join(VALID_TARGET_TIERS)}")
        return v_lower


# ==========================================
# Subscription Management Endpoints
# ==========================================

@router.post("/refund")
@limiter.limit("10/minute")
async def adm_refund(request: Request, req: AdminRefundRequest, admin: dict = Depends(require_admin)):
    """
    Admin refund operation (full or partial) with safety checks.
    """
    db = get_database_client()
    users_repo = SupabaseUserRepository(db)
    payment_repo = SupabasePaymentRepository(db)
    admin_repo = SupabaseAdminUsersRepository(db)

    user = await users_repo.get_profile(req.user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    # Safety check: ensure user_code matches profile
    stored_user_code = user.get("user_code")
    if not stored_user_code:
        raise HTTPException(400, "User has no user code assigned")
    if stored_user_code != req.user_code:
        raise HTTPException(403, "User code does not match. Please verify the user code.")
    
    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(400, "User has no Stripe customer ID")
    
    # Fetch PaymentIntent details
    pi = get_payment_intent_details(req.payment_intent_id)
    if not pi:
        raise HTTPException(404, "Payment not found")
    
    if pi.customer != customer_id:
        raise HTTPException(403, "Payment does not belong to this user")
    
    if pi.status != 'succeeded':
        raise HTTPException(400, f"Cannot refund payment with status: {pi.status}")
    
    refundable_amount = pi.amount_received if hasattr(pi, 'amount_received') else pi.amount
    
    if refundable_amount <= 0:
        raise HTTPException(400, "Payment has already been fully refunded")
    
    if req.amount_cents is not None:
        if req.amount_cents <= 0:
            raise HTTPException(400, "Refund amount must be positive")
        if req.amount_cents > refundable_amount:
            raise HTTPException(400, f"Refund amount ({req.amount_cents}) exceeds refundable amount ({refundable_amount})")
    
    result = create_refund(
        req.payment_intent_id,
        amount_cents=req.amount_cents,
        reason="requested_by_customer"
    )

    if not result["success"]:
        # v3.25: SUB-LOW-1 - Limit error exposure
        logger.error(f"[Admin] Refund failed for PI {req.payment_intent_id}: {result['error']}")
        raise HTTPException(400, "Refund operation failed")

    refund = result["refund"]
    refund_amount = refund.amount
    currency = refund.currency.upper()

    await payment_repo.create(
        user_id=req.user_id,
        amount=-refund_amount / 100,  # Convert cents to dollars, negative for refund
        currency=currency,
        payment_type="refund",
        stripe_payment_id=refund.id,
        metadata={
            "payment_intent_id": req.payment_intent_id,
            "original_amount": pi.amount,
            "refundable_amount": refundable_amount,
            "reason": req.reason,
            "admin_id": admin["id"]
        }
    )

    await admin_repo.admin_log_operation(
        admin_id=admin["id"],
        operation_type="refund",
        target_user_id=req.user_id,
        details=f"${refund_amount/100:.2f} {currency} (PI: {req.payment_intent_id[:20]}...)",
        reason=req.reason
    )
    
    return {
        "status": "refunded",
        "refund_id": refund.id,
        "amount": refund_amount,
        "currency": currency
    }


@router.post("/subscription/cancel")
@limiter.limit("10/minute")
async def adm_cancel_subscription(request: Request, req: AdminCancelSubscriptionRequest, admin: dict = Depends(require_admin)):
    """
    Admin-initiated subscription cancellation.
    """
    import stripe

    db = get_database_client()
    users_repo = SupabaseUserRepository(db)
    payment_repo = SupabasePaymentRepository(db)
    admin_repo = SupabaseAdminUsersRepository(db)

    user = await users_repo.get_profile(req.user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    stored_user_code = user.get("user_code")
    if not stored_user_code:
        raise HTTPException(400, "User has no user code assigned")
    if stored_user_code != req.user_code:
        raise HTTPException(403, "User code does not match. Please verify the user code.")
    
    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(400, "User has no Stripe customer ID")
    
    try:
        subscription_detail = stripe.Subscription.retrieve(req.subscription_id)
    except stripe.error.StripeError as e:
        # v3.25: SUB-LOW-1 - Limit Stripe error exposure
        logger.error(f"[Admin] Subscription retrieve failed: {e}")
        raise HTTPException(404, "Subscription not found or access denied")
    
    if subscription_detail.customer != customer_id:
        raise HTTPException(403, "Subscription does not belong to this user")
    
    if subscription_detail.status not in ['active', 'trialing', 'past_due']:
        raise HTTPException(400, f"Cannot cancel subscription with status: {subscription_detail.status}")
    
    if not req.immediate and subscription_detail.cancel_at_period_end:
        raise HTTPException(400, "Subscription is already scheduled for cancellation")
    
    result = cancel_subscription(req.subscription_id, immediate=req.immediate)

    if not result["success"]:
        # v3.25: SUB-LOW-1 - Limit error exposure
        logger.error(f"[Admin] Cancel subscription failed for {req.subscription_id}: {result['error']}")
        raise HTTPException(400, "Failed to cancel subscription")
    
    subscription = result["subscription"]
    
    plan_name = "Unknown"
    if subscription_detail.items.data:
        price_id = subscription_detail.items.data[0].price.id
        if 'starter' in price_id.lower():
            plan_name = "Starter"
        elif 'pro' in price_id.lower():
            plan_name = "Pro"
    
    if req.immediate:
        await users_repo.update_subscription_tier(req.user_id, "free", subscription_status="canceled")
        await payment_repo.create(
            user_id=req.user_id,
            amount=0,
            currency="USD",
            payment_type="sub_canceled",
            metadata={
                "plan_name": plan_name,
                "subscription_id": req.subscription_id,
                "reason": req.reason,
                "admin_id": admin["id"]
            }
        )
    else:
        await payment_repo.create(
            user_id=req.user_id,
            amount=0,
            currency="USD",
            payment_type="sub_cancel_scheduled",
            metadata={
                "plan_name": plan_name,
                "subscription_id": req.subscription_id,
                "period_end": str(subscription.current_period_end),
                "reason": req.reason,
                "admin_id": admin["id"]
            }
        )

    await admin_repo.admin_log_operation(
        admin_id=admin["id"],
        operation_type="subscription_cancel",
        target_user_id=req.user_id,
        details=f"{plan_name} ({'immediate' if req.immediate else 'at period end'})",
        reason=req.reason
    )
    
    return {
        "status": "canceled" if req.immediate else "cancel_scheduled",
        "subscription_id": subscription.id,
        "cancel_at_period_end": subscription.cancel_at_period_end,
        "current_period_end": subscription.current_period_end
    }


@router.post("/subscription/downgrade")
@limiter.limit("10/minute")
async def adm_downgrade_subscription(request: Request, req: AdminDowngradeRequest, admin: dict = Depends(require_admin)):
    """
    Admin-assisted subscription downgrade.
    """
    import stripe

    db = get_database_client()
    supabase = get_supabase_client()
    users_repo = SupabaseUserRepository(db)
    payment_repo = SupabasePaymentRepository(db)
    admin_repo = SupabaseAdminUsersRepository(db)

    user = await users_repo.get_profile(req.user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    stored_user_code = user.get("user_code")
    if not stored_user_code:
        raise HTTPException(400, "User has no user code assigned")
    if stored_user_code != req.user_code:
        raise HTTPException(403, "User code does not match")
    
    if user.get("email") != req.user_email:
        raise HTTPException(403, "User email does not match")
    
    current_tier = user.get("tier", "free")
    target_tier = req.target_tier.lower()
    
    tier_levels = {"free": 0, "starter": 1, "pro": 2}
    if tier_levels.get(target_tier, -1) >= tier_levels.get(current_tier, 0):
        raise HTTPException(400, f"Cannot downgrade from {current_tier} to {target_tier}")

    customer_id = user.get("stripe_customer_id")
    
    # Case 1: downgrading to Free
    if target_tier == "free":
        if not customer_id:
            await users_repo.update_subscription_tier(req.user_id, "free", subscription_status="inactive")
            await users_repo.update_monthly_credits(req.user_id, TIER_MONTHLY_CREDITS["free"])

            await payment_repo.create(
                user_id=req.user_id,
                amount=0,
                currency="USD",
                payment_type="tier_downgrade",
                metadata={
                    "from_tier": current_tier,
                    "to_tier": "free",
                    "immediate": req.immediate,
                    "reason": req.reason,
                    "admin_id": admin["id"]
                }
            )
            return {"status": "downgraded", "from_tier": current_tier, "to_tier": "free"}
        
        subscriptions = get_customer_subscriptions(customer_id)
        active_sub = next((sub for sub in subscriptions if sub.status in ['active', 'trialing']), None)

        if not active_sub:
            await users_repo.update_subscription_tier(req.user_id, "free", subscription_status="inactive")
            await users_repo.update_monthly_credits(req.user_id, TIER_MONTHLY_CREDITS["free"])

            await payment_repo.create(
                user_id=req.user_id,
                amount=0,
                currency="USD",
                payment_type="tier_downgrade",
                metadata={
                    "from_tier": current_tier,
                    "to_tier": "free",
                    "reason": req.reason,
                    "admin_id": admin["id"]
                }
            )
            return {"status": "downgraded", "from_tier": current_tier, "to_tier": "free"}

        if req.immediate:
            result = cancel_subscription(active_sub.id, immediate=True)
            if not result["success"]:
                # v3.25: SUB-LOW-1 - Limit error exposure
                logger.error(f"[Admin] Failed to cancel subscription {active_sub.id}: {result['error']}")
                raise HTTPException(400, "Failed to cancel subscription")

            await users_repo.update_subscription_tier(req.user_id, "free", subscription_status="canceled")
            await users_repo.update_monthly_credits(req.user_id, TIER_MONTHLY_CREDITS["free"])

            await payment_repo.create(
                user_id=req.user_id,
                amount=0,
                currency="USD",
                payment_type="tier_downgrade",
                metadata={
                    "from_tier": current_tier,
                    "to_tier": "free",
                    "immediate": True,
                    "subscription_id": active_sub.id,
                    "reason": req.reason,
                    "admin_id": admin["id"]
                }
            )
        else:
            result = cancel_subscription(active_sub.id, immediate=False)
            if not result["success"]:
                # v3.25: SUB-LOW-1 - Limit error exposure
                logger.error(f"[Admin] Failed to schedule cancellation for {active_sub.id}: {result['error']}")
                raise HTTPException(400, "Failed to schedule cancellation")

            await payment_repo.create(
                user_id=req.user_id,
                amount=0,
                currency="USD",
                payment_type="tier_downgrade_scheduled",
                metadata={
                    "from_tier": current_tier,
                    "to_tier": "free",
                    "period_end": str(result['subscription'].current_period_end),
                    "subscription_id": active_sub.id,
                    "reason": req.reason,
                    "admin_id": admin["id"]
                }
            )
        
        return {
            "status": "downgraded" if req.immediate else "downgrade_scheduled",
            "from_tier": current_tier,
            "to_tier": "free",
            "subscription_id": active_sub.id
        }
    
    # Case 2: Pro → Starter
    if current_tier == "pro" and target_tier == "starter":
        if not customer_id:
            raise HTTPException(400, "User has no Stripe customer ID for subscription change")
        
        subscriptions = get_customer_subscriptions(customer_id)
        active_sub = next((sub for sub in subscriptions if sub.status in ['active', 'trialing']), None)
        
        if not active_sub:
            raise HTTPException(400, "No active subscription found to downgrade")
        
        starter_price_id = os.environ.get("STRIPE_STARTER_MONTHLY_PRICE_ID")
        if not starter_price_id:
            raise HTTPException(500, "Starter price ID not configured")
        
        try:
            updated_sub = stripe.Subscription.modify(
                active_sub.id,
                items=[{
                    "id": active_sub.items.data[0].id,
                    "price": starter_price_id
                }],
                proration_behavior='create_prorations' if req.immediate else 'none',
                billing_cycle_anchor='unchanged' if not req.immediate else 'now'
            )

            if req.immediate:
                await users_repo.update_subscription_tier(req.user_id, "starter", subscription_status="active")
                await users_repo.update_monthly_credits(req.user_id, TIER_MONTHLY_CREDITS["starter"])

                await payment_repo.create(
                    user_id=req.user_id,
                    amount=0,
                    currency="USD",
                    payment_type="tier_downgrade",
                    metadata={
                        "from_tier": "pro",
                        "to_tier": "starter",
                        "immediate": True,
                        "subscription_id": active_sub.id,
                        "reason": req.reason,
                        "admin_id": admin["id"]
                    }
                )
            else:
                await payment_repo.create(
                    user_id=req.user_id,
                    amount=0,
                    currency="USD",
                    payment_type="tier_downgrade_scheduled",
                    metadata={
                        "from_tier": "pro",
                        "to_tier": "starter",
                        "next_billing": str(updated_sub.current_period_end),
                        "subscription_id": active_sub.id,
                        "reason": req.reason,
                        "admin_id": admin["id"]
                    }
                )

            await admin_repo.admin_log_operation(
                admin_id=admin["id"],
                operation_type="subscription_downgrade",
                target_user_id=req.user_id,
                details=f"Pro → Starter ({'immediate' if req.immediate else 'at period end'})",
                reason=req.reason
            )
            
            return {
                "status": "downgraded" if req.immediate else "downgrade_scheduled",
                "from_tier": "pro",
                "to_tier": "starter",
                "subscription_id": active_sub.id
            }
            
        except stripe.error.StripeError as e:
            # v3.25: SUB-LOW-1 - Limit Stripe error exposure
            logger.error(f"[Admin] Subscription downgrade failed: {e}")
            raise HTTPException(400, "Subscription modification failed")
    
    raise HTTPException(400, "Invalid downgrade path")
