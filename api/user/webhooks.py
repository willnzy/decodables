"""
Webhooks API - Third-party webhook handlers (v2).

@module api.user.webhooks
@version 2.4.0

Changes in v2.4.0:
- W-P0-1: Stripe signature header required (not optional)
- W-P0-2: Subscription creation with atomic operations
- W-P0-3: Credit purchase order fixed (payment record first)
- W-HIGH-1: Signup bonus uses INSERT ON CONFLICT for atomicity
- W-HIGH-2: Renewal with transaction consistency
- W-HIGH-3: Proper status handling for subscription states
- W-MEDIUM-*: Improved error handling and logging

v2.3.0: Metadata validation, error logging, idempotency improvements
v2.2.0: Support for credits_500, credits_2000, get_credits_amount()
v2.1.0: Idempotency, customer_id validation, get_tier_from_price_id()

Endpoints:
- POST /api/v2/user/webhooks/clerk - Clerk user events
- POST /api/v2/user/webhooks/stripe - Stripe payment events
"""

import logging
from fastapi import APIRouter, Request, Header, HTTPException

from svix.webhooks import Webhook, WebhookVerificationError

from config import CLERK_WEBHOOK_SECRET
from core.database import get_supabase_client
from infrastructure.repositories import (
    SupabaseUserRepository,
    SupabaseCreditRepository,
    SupabasePaymentRepository,
)
from domains.billing.payment_service import construct_event, get_tier_from_price_id, get_credits_amount
from domains.platform.analytics_service import AnalyticsEvents, track_payment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["user-webhooks-v2"])


# ==========================================
# Clerk Webhook
# ==========================================

@router.post("/clerk")
async def clerk_webhook(request: Request):
    """
    Clerk webhook handler for user events.

    Handles:
    - user.created: Create new user profile
    - user.updated: Sync profile changes
    - session.created: Log login
    - session.ended/removed/revoked: Log logout

    **Update webhook URL in Clerk Dashboard:**
    1. Go to https://dashboard.clerk.com
    2. Select your application
    3. Navigate to "Webhooks" in the sidebar
    4. Update endpoint URL to: https://your-domain.com/api/v2/user/webhooks/clerk
    5. Subscribe to events: user.created, user.updated, session.created, session.ended
    """
    if not CLERK_WEBHOOK_SECRET:
        raise HTTPException(500, "Missing CLERK_WEBHOOK_SECRET")

    payload = await request.body()
    headers = request.headers
    try:
        wh = Webhook(CLERK_WEBHOOK_SECRET)
        evt = wh.verify(payload, headers)
    except WebhookVerificationError:
        raise HTTPException(400, "Invalid signature")

    event_type = evt["type"]
    data = evt["data"]

    user_repo = SupabaseUserRepository(get_supabase_client())
    supabase = get_supabase_client()

    if event_type == "user.created":
        user_id = data["id"]
        email = data["email_addresses"][0]["email_address"]
        username = data.get("username")
        image_url = data.get("image_url")
        first_name = data.get("first_name")
        last_name = data.get("last_name")

        # Check whether the user already exists (may have been created via JIT)
        existing_profile = await user_repo.get_profile(user_id)
        if existing_profile:
            # Update missing info for the existing JIT-created user
            await user_repo.update_profile(user_id, avatar_url=image_url, username=username, first_name=first_name, last_name=last_name)
            # If email is missing, update it separately
            if not existing_profile.get("email") and email:
                supabase.table("profiles").update({"email": email}).eq("id", user_id).execute()
            logger.info(f"✅ User {user_id} already exists (JIT created), updated profile info")
            return {"status": "updated", "reason": "jit_created"}

        # Ensure email uniqueness (avoid duplicate accounts)
        existing_by_email = await user_repo.search_users(email)
        if existing_by_email:
            logger.warning(f"⚠️ User with email {email} already exists, skipping creation")
            return {"status": "skipped", "reason": "email_exists"}

        # Create a full profile (including names)
        await user_repo.create_profile(user_id, email, username, image_url, first_name=first_name, last_name=last_name)

        # v2.4.0: W-HIGH-1 fix - Grant signup bonus with atomic idempotency
        # Uses INSERT ON CONFLICT to prevent race condition between check and insert
        try:
            idempotency_key = f"signup_bonus_{user_id}"
            result = supabase.rpc("grant_signup_bonus_atomic", {
                "p_user_id": user_id,
                "p_amount": 50,
                "p_idempotency_key": idempotency_key
            }).execute()

            if result.data and result.data.get("granted"):
                logger.info(f"✅ Granted 50 signup bonus credits to user {user_id}")
            elif result.data and result.data.get("already_exists"):
                logger.info(f"✅ Signup bonus already granted to user {user_id}, skipping")
            else:
                logger.warning(f"Signup bonus result unknown for user {user_id}: {result.data}")
        except Exception as e:
            # Fallback to legacy method if RPC doesn't exist
            logger.warning(f"Atomic signup bonus RPC not available, using legacy: {e}")
            credit_repo = SupabaseCreditRepository(supabase)
            try:
                idempotency_key = f"signup_bonus_{user_id}"
                existing = await credit_repo.check_idempotency(idempotency_key)
                if existing:
                    logger.info(f"✅ Signup bonus already granted to user {user_id}, skipping")
                else:
                    await credit_repo.add_credits_permanent(
                        user_id,
                        50,
                        "Welcome bonus for new users",
                        "signup_bonus"
                    )
                    # Best effort to update idempotency key
                    try:
                        supabase.table("credit_transactions").update({
                            "idempotency_key": idempotency_key
                        }).eq("user_id", user_id).eq("type", "signup_bonus").execute()
                    except Exception:
                        pass
                    logger.info(f"✅ Granted 50 signup bonus credits to user {user_id}")
            except Exception as inner_e:
                logger.error(f"Failed to grant signup bonus to user {user_id}: {inner_e}")

        # Log signup event
        try:
            supabase.table("activity_logs").insert({
                "user_id": user_id,
                "action": "user_signup",
                "metadata": {
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "method": "clerk"
                },
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to log signup activity: {e}")

    elif event_type == "user.updated":
        # User updated avatar/username/names
        user_id = data.get("id")
        new_avatar = data.get("image_url")
        new_username = data.get("username")
        new_first_name = data.get("first_name")
        new_last_name = data.get("last_name")

        # Sync updates to Supabase (including name fields)
        await user_repo.update_profile(user_id, avatar_url=new_avatar, username=new_username, first_name=new_first_name, last_name=new_last_name)

        # Log profile update
        try:
            supabase.table("activity_logs").insert({
                "user_id": user_id,
                "action": "profile_updated",
                "metadata": {
                    "avatar_changed": new_avatar is not None,
                    "username_changed": new_username is not None,
                    "name_changed": new_first_name is not None or new_last_name is not None
                },
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to log profile update: {e}")
        logger.info(f"✅ Updated profile for user {user_id}")

    elif event_type == "session.created":
        # Log login event
        user_id = data.get("user_id")
        if user_id:
            try:
                supabase.table("activity_logs").insert({
                    "user_id": user_id,
                    "action": "user_login",
                    "metadata": {
                        "client_ip": evt.get("event_attributes", {}).get("http_request", {}).get("client_ip"),
                        "user_agent": evt.get("event_attributes", {}).get("http_request", {}).get("user_agent")
                    },
                }).execute()
            except Exception as e:
                logger.warning(f"Failed to log login: {e}")

    elif event_type in ["session.ended", "session.removed", "session.revoked"]:
        # Log logout event
        user_id = data.get("user_id")
        if user_id:
            try:
                supabase.table("activity_logs").insert({
                    "user_id": user_id,
                    "action": "user_logout",
                    "metadata": {"reason": event_type},
                }).execute()
            except Exception as e:
                logger.warning(f"Failed to log logout: {e}")

    return {"status": "processed"}


# ==========================================
# Stripe Webhook
# ==========================================

@router.post("/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(..., alias="Stripe-Signature")):
    """
    Stripe webhook handler with idempotency protection.

    v3.22: Added idempotency check via PostgreSQL RPC to prevent duplicate processing.
    Stripe may send the same webhook multiple times, this ensures we only process once.

    Handles:
    - checkout.session.completed: Credits purchase or subscription start
    - invoice.payment_succeeded: Subscription renewal
    - customer.subscription.deleted/updated: Subscription changes

    **Update webhook URL in Stripe Dashboard:**
    1. Go to https://dashboard.stripe.com/webhooks
    2. Click on your existing webhook endpoint
    3. Update "Endpoint URL" to: https://your-domain.com/api/v2/user/webhooks/stripe
    4. Ensure these events are selected:
       - checkout.session.completed
       - invoice.payment_succeeded
       - customer.subscription.deleted
       - customer.subscription.updated
    5. Save changes and copy the new signing secret to STRIPE_WEBHOOK_SECRET env var
    """
    supabase = get_supabase_client()
    payload = await request.body()
    try:
        event = construct_event(payload, stripe_signature)
    except Exception as e:
        # Don't expose internal error details
        logger.error(f"[Webhook] Stripe signature verification failed: {e}")
        raise HTTPException(400, "Invalid signature")

    event_id = event.get('id')
    event_type = event.get('type')

    # v2.3.0: Validate event_id and event_type
    if not event_id:
        logger.error(f"[Webhook] Received Stripe event without id")
        raise HTTPException(400, "Invalid event: missing id")
    if not event_type:
        logger.error(f"[Webhook] Received Stripe event without type: {event_id}")
        raise HTTPException(400, "Invalid event: missing type")

    # v3.22: Idempotency check - prevent duplicate event processing
    try:
        idempotency_result = supabase.rpc("check_webhook_idempotency", {
            "p_event_id": event_id,
            "p_event_type": event_type,
            "p_payload": event
        }).execute()

        check_data = idempotency_result.data
        if check_data and check_data.get("idempotent"):
            # Event already processed, return success
            logger.info(f"[Webhook] Duplicate event ignored: {event_id} ({event_type})")
            return {"status": "already_processed", "event_id": event_id}
    except Exception as e:
        # v2.3.0: Fail-safe - if idempotency check fails for critical events, reject
        # For non-critical events, log and continue
        critical_events = ['checkout.session.completed', 'invoice.payment_succeeded']
        if event_type in critical_events:
            logger.error(f"[Webhook] CRITICAL: Idempotency check failed for {event_type}, rejecting: {e}")
            raise HTTPException(503, "Webhook processing temporarily unavailable")
        else:
            logger.warning(f"[Webhook] Idempotency check failed for {event_id}: {e}")

    process_result = {"status": "ok"}

    # One-time purchase completed
    if event_type == 'checkout.session.completed':
        process_result = await _handle_checkout_completed(event)

    # Subscription renewal (monthly refresh)
    elif event_type == 'invoice.payment_succeeded':
        process_result = await _handle_invoice_payment(event)

    # Subscription canceled or expired
    elif event_type in ['customer.subscription.deleted', 'customer.subscription.updated']:
        process_result = await _handle_subscription_change(event)

    # v3.22: Update webhook result for logging
    try:
        supabase.rpc("update_webhook_result", {
            "p_event_id": event_id,
            "p_result": process_result
        }).execute()
    except Exception as e:
        logger.warning(f"[Webhook] Failed to update result for {event_id}: {e}")

    return process_result


# ==========================================
# Helper Functions
# ==========================================

async def _handle_checkout_completed(event: dict) -> dict:
    """
    Handle checkout.session.completed event.

    v2.4.0: W-P0-2/3 fix - Proper transaction order:
    1. Payment record FIRST (establishes audit trail)
    2. Then credits/tier update (the actual benefit)
    3. Activity logging and analytics (non-critical)
    """
    session = event['data']['object']
    session_id = session.get('id', 'unknown')

    # v2.3.0: Validate metadata exists
    metadata = session.get('metadata', {})
    if not metadata:
        logger.error(f"[Webhook] checkout.session.completed missing metadata: session={session_id}")
        return {"status": "error", "error": "missing_metadata", "session_id": session_id}

    uid = metadata.get('user_id')
    plan = metadata.get('plan_type')

    # v2.3.0: Validate required fields
    if not uid or not plan:
        logger.error(f"[Webhook] checkout.session.completed incomplete metadata: uid={uid}, plan={plan}, session={session_id}")
        return {"status": "error", "error": "incomplete_metadata", "session_id": session_id}

    amount_total = session.get('amount_total', 0)  # Amount in cents
    currency = session.get('currency', 'usd').upper()

    # v2.3.0: Validate amount
    if amount_total <= 0:
        logger.error(f"[Webhook] Invalid amount for checkout {session_id}: {amount_total}")
        return {"status": "error", "error": "invalid_amount", "session_id": session_id}

    if uid and plan:
        user_repo = SupabaseUserRepository(get_supabase_client())
        credit_repo = SupabaseCreditRepository(get_supabase_client())
        payment_repo = SupabasePaymentRepository(get_supabase_client())
        supabase = get_supabase_client()

        # Handle credits purchase (credits_100, credits_500, credits_2000)
        credits_amount = get_credits_amount(plan)
        if credits_amount > 0:
            # v2.4.0: W-P0-3 fix - Log payment FIRST (audit trail before benefit)
            try:
                await payment_repo.create(
                    uid, amount_total, currency, "credits_purchase",
                    metadata={"description": f"Purchase {credits_amount} Credits - ${amount_total/100:.2f}", "session_id": session_id}
                )
            except Exception as e:
                logger.error(f"[Webhook] Failed to record payment for user {uid}: {e}")
                return {"status": "error", "error": "payment_record_failed", "session_id": session_id}

            # Now add credits (only after payment is recorded)
            try:
                await credit_repo.add_credits_permanent(uid, credits_amount, f"Purchase {credits_amount} Credits", "topup_purchase")
            except Exception as e:
                logger.error(f"[Webhook] CRITICAL: Payment recorded but credits failed for user {uid}: {e}")
                # Payment was recorded, manual intervention needed
                return {"status": "partial_error", "error": "credits_add_failed", "session_id": session_id, "user_id": uid}

            # Log activity (non-critical)
            try:
                supabase.table("activity_logs").insert({
                    "user_id": uid,
                    "action": "credits_purchase",
                    "metadata": {"amount": credits_amount, "payment": amount_total, "session_id": session_id},
                }).execute()
            except Exception as e:
                logger.warning(f"Failed to log activity: {e}")

            # Analytics: Track credits purchase (non-critical)
            try:
                track_payment(uid, AnalyticsEvents.CREDITS_PURCHASED, amount_total, currency, extra_properties={"credits_amount": credits_amount})
            except Exception as e:
                logger.warning(f"Failed to track analytics: {e}")

            return {"status": "ok", "action": "credits_added", "user_id": uid, "credits": credits_amount}

        elif plan in ['starter', 'pro']:
            # v2.4.0: W-P0-2 fix - Validate customer_id first
            stripe_customer_id = session.get('customer')
            if not stripe_customer_id:
                logger.error(f"[Webhook] Missing customer_id in checkout session for user {uid}")
                return {"status": "error", "error": "missing_customer_id", "user_id": uid}

            amt = 500 if plan == 'starter' else 1000

            # v2.4.0: W-P0-2 fix - Use atomic RPC for subscription creation
            # This ensures tier, credits, and payment are all updated atomically
            try:
                result = supabase.rpc("process_subscription_start", {
                    "p_user_id": uid,
                    "p_plan": plan,
                    "p_stripe_customer_id": stripe_customer_id,
                    "p_credits_amount": amt,
                    "p_payment_amount": amount_total,
                    "p_currency": currency,
                    "p_session_id": session_id
                }).execute()

                if not result.data or not result.data.get("success"):
                    error_msg = result.data.get("error") if result.data else "Unknown error"
                    logger.error(f"[Webhook] Atomic subscription start failed for user {uid}: {error_msg}")
                    return {"status": "error", "error": "subscription_start_failed", "user_id": uid}

            except Exception as e:
                # Fallback to non-atomic (legacy) flow if RPC doesn't exist
                logger.warning(f"[Webhook] Atomic RPC not available, using legacy flow: {e}")
                try:
                    # Legacy flow: payment first, then tier, then credits
                    await payment_repo.create(
                        uid, amount_total, currency, "sub_payment",
                        metadata={"description": f"{plan.capitalize()} Plan Subscription - ${amount_total/100:.2f}", "session_id": session_id}
                    )
                    await user_repo.update_subscription_tier(uid, plan, stripe_customer_id, "active")
                    await credit_repo.add_credits_monthly(uid, amt, f"{plan.capitalize()} Monthly Credits", "sub_grant")
                except Exception as legacy_error:
                    logger.error(f"[Webhook] Legacy subscription flow failed for user {uid}: {legacy_error}")
                    return {"status": "error", "error": "subscription_start_failed", "user_id": uid}

            # Log activity (non-critical)
            try:
                supabase.table("activity_logs").insert({
                    "user_id": uid,
                    "action": "subscription_started",
                    "metadata": {"plan": plan, "payment": amount_total, "session_id": session_id},
                }).execute()
            except Exception as e:
                logger.warning(f"Failed to log activity: {e}")

            # Analytics: Track subscription started (non-critical)
            try:
                track_payment(uid, AnalyticsEvents.CHECKOUT_COMPLETED, amount_total, currency, plan=plan)
            except Exception as e:
                logger.warning(f"Failed to track analytics: {e}")

            return {"status": "ok", "action": "subscription_started", "user_id": uid, "plan": plan}

    return {"status": "ok"}


async def _handle_invoice_payment(event: dict) -> dict:
    """
    Handle invoice.payment_succeeded event.

    v2.4.0: W-HIGH-2/3 fix - Proper transaction handling:
    1. Validate customer and user first
    2. Record payment before refreshing credits
    3. Handle partial failures gracefully
    """
    invoice = event['data']['object']
    invoice_id = invoice.get('id', 'unknown')
    customer_id = invoice.get('customer')
    amount_paid = invoice.get('amount_paid', 0)  # Amount in cents
    currency = invoice.get('currency', 'usd').upper()
    billing_reason = invoice.get('billing_reason', '')  # subscription_create, subscription_cycle, etc.

    # v2.3.0: Validate customer_id
    if not customer_id:
        logger.error(f"[Webhook] invoice.payment_succeeded missing customer_id: invoice={invoice_id}")
        return {"status": "error", "error": "missing_customer_id", "invoice_id": invoice_id}

    supabase = get_supabase_client()
    # Match via stripe_customer_id
    user_res = supabase.table("profiles").select("id, tier, subscription_status")\
        .eq("stripe_customer_id", customer_id).execute()

    if not user_res.data:
        # v2.3.0: Log warning when user not found
        logger.warning(f"[Webhook] No user found for customer {customer_id}: invoice={invoice_id}")
        return {"status": "error", "error": "user_not_found", "customer_id": customer_id}

    user = user_res.data[0]
    uid = user['id']
    # v2.3.0: Safe tier access with default
    tier = user.get('tier', 'free')
    current_status = user.get('subscription_status', 'inactive')

    # Refresh monthly credits (reset, no rollover) on renewal
    if tier in ['starter', 'pro'] and billing_reason == 'subscription_cycle':
        payment_repo = SupabasePaymentRepository(get_supabase_client())

        # v2.4.0: W-HIGH-2 fix - Record payment FIRST (audit trail)
        try:
            await payment_repo.create(
                uid, amount_paid, currency, "sub_renewal",
                metadata={"description": f"{tier.capitalize()} Plan Renewal - ${amount_paid/100:.2f}", "invoice_id": invoice_id}
            )
        except Exception as e:
            logger.error(f"[Webhook] Failed to record renewal payment for user {uid}: {e}")
            return {"status": "error", "error": "payment_record_failed", "invoice_id": invoice_id}

        # v2.4.0: W-HIGH-3 fix - Handle subscription status properly
        # Ensure subscription is marked as active after successful payment
        if current_status != 'active':
            try:
                supabase.table("profiles").update({
                    "subscription_status": "active"
                }).eq("id", uid).execute()
                logger.info(f"[Webhook] Reactivated subscription for user {uid}")
            except Exception as e:
                logger.warning(f"[Webhook] Failed to update subscription status for user {uid}: {e}")

        # Now refresh credits
        credit_repo = SupabaseCreditRepository(get_supabase_client())
        try:
            await credit_repo.refresh_monthly_credits(uid, tier)
        except Exception as e:
            logger.error(f"[Webhook] CRITICAL: Payment recorded but credits refresh failed for user {uid}: {e}")
            return {"status": "partial_error", "error": "credits_refresh_failed", "invoice_id": invoice_id, "user_id": uid}

        # Log activity (non-critical)
        try:
            supabase.table("activity_logs").insert({
                "user_id": uid,
                "action": "monthly_credits_refreshed",
                "metadata": {"tier": tier, "payment": amount_paid, "invoice_id": invoice_id},
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to log activity: {e}")

        return {"status": "ok", "action": "credits_refreshed", "user_id": uid}

    # v2.4.0: W-HIGH-3 fix - Handle subscription_create billing reason
    # This occurs on first subscription, ensure status is active
    if billing_reason == 'subscription_create' and tier in ['starter', 'pro']:
        if current_status != 'active':
            try:
                supabase.table("profiles").update({
                    "subscription_status": "active"
                }).eq("id", uid).execute()
                logger.info(f"[Webhook] Confirmed subscription active for user {uid}")
            except Exception as e:
                logger.warning(f"[Webhook] Failed to confirm subscription status for user {uid}: {e}")

    return {"status": "ok"}


async def _handle_subscription_change(event: dict) -> dict:
    """
    Handle customer.subscription.deleted/updated events.

    v2.4.0: W-MEDIUM-* fix - Improved error handling and logging:
    1. Better status handling for edge cases
    2. Structured logging with context
    3. Graceful degradation on failures
    """
    subscription = event['data']['object']
    subscription_id = subscription.get('id', 'unknown')
    customer_id = subscription.get('customer')
    status = subscription.get('status')
    event_type = event.get('type', 'unknown')

    # v2.3.0: Validate customer_id
    if not customer_id:
        logger.warning(f"[Webhook] subscription change missing customer_id: sub={subscription_id}, event={event_type}")
        return {"status": "error", "error": "missing_customer_id", "subscription_id": subscription_id}

    # v2.4.0: Log all subscription changes for audit
    logger.info(f"[Webhook] Processing subscription change: sub={subscription_id}, status={status}, event={event_type}")

    supabase = get_supabase_client()
    user_res = supabase.table("profiles").select("id, tier")\
        .eq("stripe_customer_id", customer_id).execute()

    if not user_res.data:
        logger.warning(f"[Webhook] No user found for customer {customer_id}: sub={subscription_id}")
        return {"status": "error", "error": "user_not_found", "customer_id": customer_id}

    uid = user_res.data[0]['id']
    current_tier = user_res.data[0].get('tier', 'free')
    user_repo = SupabaseUserRepository(get_supabase_client())

    # v2.4.0: W-MEDIUM-3 fix - Handle all termination statuses
    termination_statuses = ['canceled', 'unpaid', 'past_due', 'incomplete_expired']
    if status in termination_statuses:
        # Downgrade to free
        try:
            await user_repo.update_subscription_tier(uid, 'free', subscription_status='inactive')
            logger.info(f"[Webhook] Downgraded user {uid} to free tier (was {current_tier}), reason: {status}")
        except Exception as e:
            logger.error(f"[Webhook] Failed to downgrade user {uid}: {e}")
            return {"status": "error", "error": "tier_update_failed", "user_id": uid}

        # Log activity (non-critical)
        try:
            supabase.table("activity_logs").insert({
                "user_id": uid,
                "action": "subscription_ended",
                "metadata": {"reason": status, "previous_tier": current_tier, "subscription_id": subscription_id},
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to log activity: {e}")

        return {"status": "ok", "action": "subscription_ended", "user_id": uid, "previous_tier": current_tier}

    elif status == 'active':
        # Subscription reactivated or updated
        price_id = subscription.get('items', {}).get('data', [{}])[0].get('price', {}).get('id', '')
        # Use config-based mapping instead of fragile string matching
        new_tier = get_tier_from_price_id(price_id)

        if new_tier == 'free':
            # v2.4.0: W-MEDIUM-4 fix - Better handling of unknown price_id
            logger.warning(f"[Webhook] Unknown price_id '{price_id}' for user {uid}, keeping current tier {current_tier}")
            # Don't downgrade to free for unknown price - could be a new plan not yet configured
            new_tier = current_tier if current_tier in ['starter', 'pro'] else 'free'

        try:
            # v2.3.0: Pass customer_id to ensure mapping is maintained
            await user_repo.update_subscription_tier(uid, new_tier, stripe_customer_id=customer_id, subscription_status='active')
            logger.info(f"[Webhook] Updated user {uid} subscription: {current_tier} -> {new_tier}")
        except Exception as e:
            logger.error(f"[Webhook] Failed to update subscription for user {uid}: {e}")
            return {"status": "error", "error": "tier_update_failed", "user_id": uid}

        # Log activity if tier changed
        if new_tier != current_tier:
            try:
                supabase.table("activity_logs").insert({
                    "user_id": uid,
                    "action": "subscription_changed",
                    "metadata": {"previous_tier": current_tier, "new_tier": new_tier, "subscription_id": subscription_id},
                }).execute()
            except Exception as e:
                logger.warning(f"Failed to log activity: {e}")

        return {"status": "ok", "action": "subscription_reactivated", "user_id": uid, "tier": new_tier}

    # v2.4.0: W-MEDIUM-5 fix - Handle incomplete/trialing statuses
    elif status in ['incomplete', 'trialing']:
        logger.info(f"[Webhook] Subscription in {status} state for user {uid}, no action needed")
        return {"status": "ok", "action": "no_action", "reason": f"subscription_{status}"}

    # Unknown status
    logger.warning(f"[Webhook] Unhandled subscription status '{status}' for user {uid}")
    return {"status": "ok", "action": "no_action", "reason": f"unhandled_status_{status}"}
