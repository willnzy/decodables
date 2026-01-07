"""
Admin Subscriptions API - Subscription management endpoints for admins.

@module api.admin.subscriptions_api
@version 2.0.0

Endpoints:
- POST /subscriptions/refund - Process refund
- POST /subscriptions/cancel - Cancel subscription
- POST /subscriptions/downgrade - Downgrade subscription
"""

import os
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from dependencies import require_admin
from services.db_service import (
    supabase,
    get_user_profile,
    update_subscription_tier,
    admin_log_operation,
    log_activity,
    log_payment_record,
)
from services.payment_service import (
    get_customer_subscriptions,
    cancel_subscription,
    create_refund,
    get_payment_intent_details,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["admin-subscriptions"])


# ==========================================
# Request Models
# ==========================================

class RefundRequest(BaseModel):
    user_id: str
    user_code: str  # Must match for verification
    payment_intent_id: str
    amount_cents: Optional[int] = None  # None = full refund
    reason: str


class CancelSubscriptionRequest(BaseModel):
    user_id: str
    user_code: str  # Must match for verification
    subscription_id: str
    immediate: bool = False  # True = cancel now, False = cancel at period end
    reason: str


class DowngradeRequest(BaseModel):
    user_id: str
    user_code: str  # For verification
    user_email: str  # For verification
    target_tier: str  # 'starter' | 'free'
    immediate: bool = False  # True = immediate, False = apply at period end
    reason: str


# ==========================================
# Subscription Management Endpoints
# ==========================================

@router.post("/refund")
def process_refund(
    req: RefundRequest,
    admin: dict = Depends(require_admin)
):
    """Admin refund operation (full or partial) with safety checks."""
    user = get_user_profile(req.user_id)
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
        raise HTTPException(400, f"Refund failed: {result['error']}")

    refund = result["refund"]
    refund_amount = refund.amount
    currency = refund.currency.upper()

    log_payment_record(
        req.user_id,
        -refund_amount,
        currency,
        "refund",
        f"Refund - ${refund_amount/100:.2f} | Reason: {req.reason}"
    )

    log_activity(admin["id"], "admin_refund", {
        "target_user": req.user_id,
        "payment_intent_id": req.payment_intent_id,
        "refund_id": refund.id,
        "amount_cents": refund_amount,
        "original_amount": pi.amount,
        "refundable_amount": refundable_amount,
        "reason": req.reason
    })

    admin_log_operation(
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


@router.post("/cancel")
def cancel_user_subscription(
    req: CancelSubscriptionRequest,
    admin: dict = Depends(require_admin)
):
    """Admin-initiated subscription cancellation."""
    import stripe

    user = get_user_profile(req.user_id)
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
        raise HTTPException(404, f"Subscription not found: {str(e)}")

    if subscription_detail.customer != customer_id:
        raise HTTPException(403, "Subscription does not belong to this user")

    if subscription_detail.status not in ['active', 'trialing', 'past_due']:
        raise HTTPException(400, f"Cannot cancel subscription with status: {subscription_detail.status}")

    if not req.immediate and subscription_detail.cancel_at_period_end:
        raise HTTPException(400, "Subscription is already scheduled for cancellation")

    result = cancel_subscription(req.subscription_id, immediate=req.immediate)

    if not result["success"]:
        raise HTTPException(400, f"Cancel subscription failed: {result['error']}")

    subscription = result["subscription"]

    plan_name = "Unknown"
    if subscription_detail.items.data:
        price_id = subscription_detail.items.data[0].price.id
        if 'starter' in price_id.lower():
            plan_name = "Starter"
        elif 'pro' in price_id.lower():
            plan_name = "Pro"

    if req.immediate:
        update_subscription_tier(req.user_id, "free", subscription_status="canceled")
        log_payment_record(
            req.user_id, 0, "USD", "sub_canceled",
            f"{plan_name} Subscription Canceled (Immediate) | Reason: {req.reason}"
        )
    else:
        log_payment_record(
            req.user_id, 0, "USD", "sub_cancel_scheduled",
            f"{plan_name} Subscription Cancel Scheduled | Ends: {subscription.current_period_end} | Reason: {req.reason}"
        )

    log_activity(admin["id"], "admin_cancel_subscription", {
        "target_user": req.user_id,
        "subscription_id": req.subscription_id,
        "plan": plan_name,
        "immediate": req.immediate,
        "reason": req.reason
    })

    admin_log_operation(
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


@router.post("/downgrade")
def downgrade_subscription(
    req: DowngradeRequest,
    admin: dict = Depends(require_admin)
):
    """Admin-assisted subscription downgrade."""
    import stripe

    user = get_user_profile(req.user_id)
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

    if target_tier not in ["free", "starter"]:
        raise HTTPException(400, "Invalid target tier. Must be 'free' or 'starter'")

    customer_id = user.get("stripe_customer_id")

    # Case 1: downgrading to Free
    if target_tier == "free":
        if not customer_id:
            update_subscription_tier(req.user_id, "free", subscription_status="inactive")
            supabase.table("profiles").update({"credits_monthly": 0}).eq("id", req.user_id).execute()

            log_payment_record(
                req.user_id, 0, "USD", "tier_downgrade",
                f"Downgrade from {current_tier.title()} to Free (No subscription) | Reason: {req.reason}"
            )
            log_activity(admin["id"], "admin_downgrade", {
                "target_user": req.user_id,
                "from_tier": current_tier,
                "to_tier": "free",
                "immediate": req.immediate,
                "reason": req.reason
            })
            return {"status": "downgraded", "from_tier": current_tier, "to_tier": "free"}

        subscriptions = get_customer_subscriptions(customer_id)
        active_sub = next((sub for sub in subscriptions if sub.status in ['active', 'trialing']), None)

        if not active_sub:
            update_subscription_tier(req.user_id, "free", subscription_status="inactive")
            supabase.table("profiles").update({"credits_monthly": 0}).eq("id", req.user_id).execute()

            log_payment_record(
                req.user_id, 0, "USD", "tier_downgrade",
                f"Downgrade from {current_tier.title()} to Free | Reason: {req.reason}"
            )
            log_activity(admin["id"], "admin_downgrade", {
                "target_user": req.user_id,
                "from_tier": current_tier,
                "to_tier": "free",
                "reason": req.reason
            })
            return {"status": "downgraded", "from_tier": current_tier, "to_tier": "free"}

        if req.immediate:
            result = cancel_subscription(active_sub.id, immediate=True)
            if not result["success"]:
                raise HTTPException(400, f"Failed to cancel subscription: {result['error']}")

            update_subscription_tier(req.user_id, "free", subscription_status="canceled")
            supabase.table("profiles").update({"credits_monthly": 0}).eq("id", req.user_id).execute()

            log_payment_record(
                req.user_id, 0, "USD", "tier_downgrade",
                f"Downgrade from {current_tier.title()} to Free (Immediate) | Reason: {req.reason}"
            )
        else:
            result = cancel_subscription(active_sub.id, immediate=False)
            if not result["success"]:
                raise HTTPException(400, f"Failed to schedule cancellation: {result['error']}")

            log_payment_record(
                req.user_id, 0, "USD", "tier_downgrade_scheduled",
                f"Downgrade scheduled: {current_tier.title()} to Free | Effective: {result['subscription'].current_period_end} | Reason: {req.reason}"
            )

        log_activity(admin["id"], "admin_downgrade", {
            "target_user": req.user_id,
            "from_tier": current_tier,
            "to_tier": "free",
            "immediate": req.immediate,
            "subscription_id": active_sub.id,
            "reason": req.reason
        })

        return {
            "status": "downgraded" if req.immediate else "downgrade_scheduled",
            "from_tier": current_tier,
            "to_tier": "free",
            "subscription_id": active_sub.id
        }

    # Case 2: Pro -> Starter
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
                update_subscription_tier(req.user_id, "starter", subscription_status="active")
                supabase.table("profiles").update({"credits_monthly": 500}).eq("id", req.user_id).execute()

                log_payment_record(
                    req.user_id, 0, "USD", "tier_downgrade",
                    f"Downgrade from Pro to Starter (Immediate) | Reason: {req.reason}"
                )
            else:
                log_payment_record(
                    req.user_id, 0, "USD", "tier_downgrade_scheduled",
                    f"Downgrade scheduled: Pro to Starter | Next billing: {updated_sub.current_period_end} | Reason: {req.reason}"
                )

            log_activity(admin["id"], "admin_downgrade", {
                "target_user": req.user_id,
                "from_tier": "pro",
                "to_tier": "starter",
                "immediate": req.immediate,
                "subscription_id": active_sub.id,
                "reason": req.reason
            })

            admin_log_operation(
                admin_id=admin["id"],
                operation_type="subscription_downgrade",
                target_user_id=req.user_id,
                details=f"Pro -> Starter ({'immediate' if req.immediate else 'at period end'})",
                reason=req.reason
            )

            return {
                "status": "downgraded" if req.immediate else "downgrade_scheduled",
                "from_tier": "pro",
                "to_tier": "starter",
                "subscription_id": active_sub.id
            }

        except stripe.error.StripeError as e:
            raise HTTPException(400, f"Stripe error: {str(e)}")

    raise HTTPException(400, "Invalid downgrade path")
