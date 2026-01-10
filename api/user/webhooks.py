"""
Webhooks API - Third-party webhook handlers (v2).

@module api.user.webhooks
@version 2.5.0 (DDD Architecture Upgrade - 5 Star)

Changes in v2.5.0:
- WEBHOOKS-CRITICAL-1: Added dependency injection for webhook services
- Migrated all endpoints to use Service layer with DI
- Architecture: API → Service (DI) → Repositories (100% DDD)
- Moved all business logic to ClerkWebhookService and StripeWebhookService

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
from fastapi import APIRouter, Request, Header, HTTPException, Depends

from svix.webhooks import WebhookVerificationError

from core.database import get_supabase_client
from infrastructure.repositories import (
    SupabaseUserRepository,
    SupabaseCreditRepository,
    SupabasePaymentRepository,
)
from domains.webhooks import ClerkWebhookService, StripeWebhookService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["user-webhooks-v2"])


# ==========================================
# Dependency Injection
# ==========================================

def get_clerk_webhook_service() -> ClerkWebhookService:
    """Dependency injection factory for ClerkWebhookService."""
    db = get_supabase_client()
    user_repo = SupabaseUserRepository(db)
    credit_repo = SupabaseCreditRepository(db)
    return ClerkWebhookService(user_repo, credit_repo)


def get_stripe_webhook_service() -> StripeWebhookService:
    """Dependency injection factory for StripeWebhookService."""
    db = get_supabase_client()
    user_repo = SupabaseUserRepository(db)
    credit_repo = SupabaseCreditRepository(db)
    payment_repo = SupabasePaymentRepository(db)
    return StripeWebhookService(user_repo, credit_repo, payment_repo)


# ==========================================
# Clerk Webhook
# ==========================================

@router.post("/clerk")
async def clerk_webhook(
    request: Request,
    clerk_service: ClerkWebhookService = Depends(get_clerk_webhook_service),  # v2.5.0: DI
):
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
    # v2.5.0: Verify signature via Service
    payload = await request.body()
    headers = dict(request.headers)

    try:
        event = clerk_service.verify_signature(payload, headers)
    except ValueError as e:
        # Missing CLERK_WEBHOOK_SECRET
        logger.error(f"[Clerk Webhook] Configuration error: {e}")
        raise HTTPException(500, str(e))
    except WebhookVerificationError:
        # Invalid signature
        logger.error("[Clerk Webhook] Signature verification failed")
        raise HTTPException(400, "Invalid signature")

    # v2.5.0: Handle event via Service
    result = await clerk_service.handle_event(event)
    return result


# ==========================================
# Stripe Webhook
# ==========================================

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),  # v2.4.0: Required
    stripe_service: StripeWebhookService = Depends(get_stripe_webhook_service),  # v2.5.0: DI
):
    """
    Stripe webhook handler with idempotency protection.

    v2.3.0: Added idempotency check via PostgreSQL RPC to prevent duplicate processing.
    Stripe may send the same webhook multiple times, this ensures we only process once.

    Handles:
    - checkout.session.completed: Credits purchase or subscription start
    - invoice.payment_succeeded: Subscription renewal
    - customer.subscription.deleted/updated: Subscription changes
    - charge.refunded: Refund processing (P0-010 fix)

    **Update webhook URL in Stripe Dashboard:**
    1. Go to https://dashboard.stripe.com/webhooks
    2. Click on your existing webhook endpoint
    3. Update "Endpoint URL" to: https://your-domain.com/api/v2/user/webhooks/stripe
    4. Ensure these events are selected:
       - checkout.session.completed
       - invoice.payment_succeeded
       - customer.subscription.deleted
       - customer.subscription.updated
       - charge.refunded (P0-010 fix: required for refund safety)
    5. Save changes and copy the new signing secret to STRIPE_WEBHOOK_SECRET env var
    """
    # v2.5.0: Verify signature via Service
    payload = await request.body()

    try:
        event = stripe_service.verify_signature(payload, stripe_signature)
    except Exception as e:
        # Don't expose internal error details
        logger.error(f"[Stripe Webhook] Signature verification failed: {e}")
        raise HTTPException(400, "Invalid signature")

    event_id = event.get("id")
    event_type = event.get("type")

    # v2.5.0: Idempotency check via Service
    try:
        if await stripe_service.is_duplicate_event(event_id, event_type, event):
            return {"status": "already_processed", "event_id": event_id}
    except Exception:
        # Critical event rejection is handled inside the service
        raise HTTPException(503, "Webhook processing temporarily unavailable")

    # v2.5.0: Handle event via Service
    process_result = await stripe_service.handle_event(event)

    # v2.5.0: Update webhook result (optional, non-blocking)
    await stripe_service.update_webhook_result(event_id, process_result)

    return process_result
