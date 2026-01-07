"""
Webhooks API - Third-party webhook handlers (v2).

@module api.user.webhooks
@version 2.0.0

Endpoints:
- POST /api/v2/user/webhooks/clerk - Clerk user events
- POST /api/v2/user/webhooks/stripe - Stripe payment events

Note: Both v1 (/api/webhooks/*) and v2 (/api/v2/user/webhooks/*) URLs are supported.
Update webhook URLs in third-party dashboards to use v2 when ready.
"""

import logging
from fastapi import APIRouter, Request, Header, HTTPException

from svix.webhooks import Webhook, WebhookVerificationError

from config import CLERK_WEBHOOK_SECRET
from core.database import get_supabase_client
from infrastructure.repositories import (
    SupabaseUserRepositoryExtended,
    SupabaseCreditRepositoryExtended,
    SupabasePaymentRepository,
)
from domains.billing.payment_service import construct_event
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

    user_repo = SupabaseUserRepositoryExtended(get_supabase_client())
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

        # Log signup event
        try:
            supabase.table("activity_logs").insert({
                "user_id": user_id,
                "activity_type": "user_signup",
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
                "activity_type": "profile_updated",
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
                    "activity_type": "user_login",
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
                    "activity_type": "user_logout",
                    "metadata": {"reason": event_type},
                }).execute()
            except Exception as e:
                logger.warning(f"Failed to log logout: {e}")

    return {"status": "processed"}


# ==========================================
# Stripe Webhook
# ==========================================

@router.post("/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
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
        raise HTTPException(400, str(e))

    event_id = event.get('id')
    event_type = event['type']

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
        # If idempotency check fails, log but continue processing
        # (better to risk double-processing than to miss events entirely)
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
    """Handle checkout.session.completed event."""
    session = event['data']['object']
    uid = session['metadata'].get('user_id')
    plan = session['metadata'].get('plan_type')
    amount_total = session.get('amount_total', 0)  # Amount in cents
    currency = session.get('currency', 'usd').upper()

    if uid and plan:
        user_repo = SupabaseUserRepositoryExtended(get_supabase_client())
        credit_repo = SupabaseCreditRepositoryExtended(get_supabase_client())
        payment_repo = SupabasePaymentRepository(get_supabase_client())
        supabase = get_supabase_client()

        if plan == 'credits_100':
            # Purchase credits -> add to permanent bucket
            await credit_repo.add_credits_permanent(uid, 100, "Purchase 100 Credits", "topup_purchase")
            # Log payment
            await payment_repo.create(uid, amount_total, currency, "credits_purchase", metadata={"description": f"Purchase 100 Credits - ${amount_total/100:.2f}"})
            # Log activity
            try:
                supabase.table("activity_logs").insert({
                    "user_id": uid,
                    "activity_type": "credits_purchase",
                    "metadata": {"amount": 100, "payment": amount_total},
                }).execute()
            except Exception as e:
                logger.warning(f"Failed to log activity: {e}")
            # Analytics: Track credits purchase
            track_payment(uid, AnalyticsEvents.CREDITS_PURCHASED, amount_total, currency, extra_properties={"credits_amount": 100})
            return {"status": "ok", "action": "credits_added", "user_id": uid}

        elif plan in ['starter', 'pro']:
            # New subscription: update tier and grant monthly credits
            await user_repo.update_subscription_tier(uid, plan, session.get('customer'), "active")
            amt = 500 if plan == 'starter' else 1000
            await credit_repo.add_credits_monthly(uid, amt, f"{plan.capitalize()} Monthly Credits", "sub_grant")
            # Log subscription payment
            await payment_repo.create(uid, amount_total, currency, "sub_payment", metadata={"description": f"{plan.capitalize()} Plan Subscription - ${amount_total/100:.2f}"})
            # Log activity
            try:
                supabase.table("activity_logs").insert({
                    "user_id": uid,
                    "activity_type": "subscription_started",
                    "metadata": {"plan": plan, "payment": amount_total},
                }).execute()
            except Exception as e:
                logger.warning(f"Failed to log activity: {e}")
            # Analytics: Track subscription started
            track_payment(uid, AnalyticsEvents.CHECKOUT_COMPLETED, amount_total, currency, plan=plan)
            return {"status": "ok", "action": "subscription_started", "user_id": uid, "plan": plan}

    return {"status": "ok"}


async def _handle_invoice_payment(event: dict) -> dict:
    """Handle invoice.payment_succeeded event."""
    invoice = event['data']['object']
    customer_id = invoice.get('customer')
    amount_paid = invoice.get('amount_paid', 0)  # Amount in cents
    currency = invoice.get('currency', 'usd').upper()
    billing_reason = invoice.get('billing_reason', '')  # subscription_create, subscription_cycle, etc.

    # Look up user
    if customer_id:
        supabase = get_supabase_client()
        # Match via stripe_customer_id
        user_res = supabase.table("profiles").select("id, tier")\
            .eq("stripe_customer_id", customer_id).execute()

        if user_res.data:
            user = user_res.data[0]
            uid = user['id']
            tier = user['tier']

            # Refresh monthly credits (reset, no rollover) on renewal
            if tier in ['starter', 'pro'] and billing_reason == 'subscription_cycle':
                credit_repo = SupabaseCreditRepositoryExtended(get_supabase_client())
                payment_repo = SupabasePaymentRepository(get_supabase_client())

                await credit_repo.refresh_monthly_credits(uid, tier)
                # Log renewal payment
                await payment_repo.create(uid, amount_paid, currency, "sub_renewal", metadata={"description": f"{tier.capitalize()} Plan Renewal - ${amount_paid/100:.2f}"})
                # Log activity
                try:
                    supabase.table("activity_logs").insert({
                        "user_id": uid,
                        "activity_type": "monthly_credits_refreshed",
                        "metadata": {"tier": tier, "payment": amount_paid},
                    }).execute()
                except Exception as e:
                    logger.warning(f"Failed to log activity: {e}")
                return {"status": "ok", "action": "credits_refreshed", "user_id": uid}

    return {"status": "ok"}


async def _handle_subscription_change(event: dict) -> dict:
    """Handle customer.subscription.deleted/updated events."""
    subscription = event['data']['object']
    customer_id = subscription.get('customer')
    status = subscription.get('status')

    if customer_id:
        supabase = get_supabase_client()
        user_res = supabase.table("profiles").select("id")\
            .eq("stripe_customer_id", customer_id).execute()

        if user_res.data:
            uid = user_res.data[0]['id']
            user_repo = SupabaseUserRepositoryExtended(get_supabase_client())

            if status in ['canceled', 'unpaid', 'past_due']:
                # Downgrade to free
                await user_repo.update_subscription_tier(uid, 'free', subscription_status='inactive')
                # Log activity
                try:
                    supabase.table("activity_logs").insert({
                        "user_id": uid,
                        "activity_type": "subscription_ended",
                        "metadata": {"reason": status},
                    }).execute()
                except Exception as e:
                    logger.warning(f"Failed to log activity: {e}")
                return {"status": "ok", "action": "subscription_ended", "user_id": uid}
            elif status == 'active':
                # Subscription reactivated
                plan_id = subscription.get('items', {}).get('data', [{}])[0].get('price', {}).get('id', '')
                # Map price_id to tier
                new_tier = 'starter' if 'starter' in plan_id.lower() else 'pro'
                await user_repo.update_subscription_tier(uid, new_tier, subscription_status='active')
                return {"status": "ok", "action": "subscription_reactivated", "user_id": uid}

    return {"status": "ok"}
