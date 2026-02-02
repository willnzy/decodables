"""
Webhooks API - Third-party webhook handlers.

@module api.user.webhooks
@version 3.0.0 (Self-hosted auth migration)

Changes in v3.0.0:
- Removed Clerk webhook endpoint (replaced by self-hosted auth)
- Removed svix dependency
- Only Stripe webhooks remain

Endpoints:
- POST /api/v2/user/webhooks/stripe - Stripe payment events
"""

import logging
from fastapi import APIRouter, Request, Header, HTTPException, Depends

from container import get_container
from domains.webhooks import StripeWebhookService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["user-webhooks-v2"])


# ==========================================
# Dependency Injection
# ==========================================

async def get_stripe_webhook_service() -> StripeWebhookService:
    """
    Dependency injection factory for StripeWebhookService via Container.
    """
    container = get_container()
    return await container.get_stripe_webhook_service()


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
        # WS-03: Structured log with request context (no secrets)
        client_ip = request.client.host if request.client else "unknown"
        logger.error(
            f"[Stripe Webhook] Signature verification failed: "
            f"ip={client_ip}, error_type={type(e).__name__}"
        )
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
