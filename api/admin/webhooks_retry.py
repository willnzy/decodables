"""
Webhook Retry Admin API

Admin endpoints for managing webhook retry logic (P3-022).

@module api.admin.webhooks_retry
@version 1.0.0

Endpoints:
- POST /api/v2/admin/webhooks/retry - Manually trigger webhook retry task
- GET /api/v2/admin/webhooks/failed - View failed webhook events
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel, Field

from dependencies import require_admin
from core.database import get_async_db_client
from infrastructure.rate_limiter import limiter
from infrastructure.repositories import (
    SupabaseWebhookRepository,
    SupabaseUserRepository,
    SupabaseCreditRepository,
    SupabasePaymentRepository,
)
from domains.webhooks import ClerkWebhookService, StripeWebhookService
from domains.webhooks.webhook_retry_service import WebhookRetryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["admin-webhooks-retry"])


# ==========================================
# Response Models
# ==========================================

class WebhookRetryStats(BaseModel):
    """Statistics from webhook retry operation."""
    processed: int = Field(..., description="Number of webhooks successfully reprocessed")
    failed: int = Field(..., description="Number of webhooks that failed retry")
    skipped: int = Field(..., description="Number of webhooks skipped (not eligible)")


class WebhookRetryResponse(BaseModel):
    """Response for webhook retry endpoint."""
    success: bool = Field(..., description="Whether retry task completed")
    message: str = Field(..., description="Human-readable message")
    stripe: WebhookRetryStats = Field(..., description="Stripe webhook stats")
    clerk: WebhookRetryStats = Field(..., description="Clerk webhook stats")
    total: WebhookRetryStats = Field(..., description="Combined stats")


class FailedWebhookEntry(BaseModel):
    """Single failed webhook entry."""
    id: str = Field(..., description="Webhook event UUID")
    event_id: str = Field(..., description="External event ID (Stripe/Clerk)")
    event_type: str = Field(..., description="Event type")
    retry_count: int = Field(..., description="Number of retry attempts")
    error_message: Optional[str] = Field(None, description="Last error message")
    created_at: str = Field(..., description="Event creation timestamp")


class FailedWebhooksResponse(BaseModel):
    """Response for failed webhooks list."""
    stripe_events: list[FailedWebhookEntry] = Field(..., description="Failed Stripe webhooks")
    clerk_events: list[FailedWebhookEntry] = Field(..., description="Failed Clerk webhooks")
    total_count: int = Field(..., description="Total number of failed webhooks")


# ==========================================
# Dependency Injection
# ==========================================

async def get_webhook_retry_service() -> WebhookRetryService:
    """Dependency injection for WebhookRetryService."""
    db = await get_async_db_client()

    # Repositories
    webhook_repo = SupabaseWebhookRepository(db)
    user_repo = SupabaseUserRepository(db)
    credit_repo = SupabaseCreditRepository(db)
    payment_repo = SupabasePaymentRepository(db)

    # Webhook Services
    clerk_service = ClerkWebhookService(user_repo, credit_repo)
    stripe_service = StripeWebhookService(user_repo, credit_repo, payment_repo)

    return WebhookRetryService(webhook_repo, clerk_service, stripe_service)


# ==========================================
# Endpoints
# ==========================================

@router.post("/retry", response_model=WebhookRetryResponse)
@limiter.limit("10/hour")  # Strict rate limit - this is expensive operation
async def retry_failed_webhooks(
    request: Request,
    admin: dict = Depends(require_admin),
    retry_service: WebhookRetryService = Depends(get_webhook_retry_service),
):
    """
    Manually trigger webhook retry task.

    Reprocesses all failed webhook events that are eligible for retry.

    **Eligibility Criteria**:
    - retry_count < max_retries (default: 5)
    - created_at within max_age (default: 72 hours)
    - Sufficient time has passed since last retry (exponential backoff)

    **Rate Limit**: 10 requests per hour (expensive operation)

    **Security**: Admin role required

    **Usage**:
    - Manual trigger via Admin UI
    - Scheduled via GitHub Actions or external cron
    - Emergency retry after fixing webhook processing bugs

    Returns:
        WebhookRetryResponse with statistics

    Example Response:
        {
            "success": true,
            "message": "Retry task completed",
            "stripe": {"processed": 5, "failed": 2, "skipped": 10},
            "clerk": {"processed": 3, "failed": 0, "skipped": 5},
            "total": {"processed": 8, "failed": 2, "skipped": 15}
        }
    """
    try:
        logger.info(f"[Admin {admin.get('id')}] Triggered webhook retry task")

        # Run retry task
        stats = await retry_service.retry_all_failed_webhooks()

        return WebhookRetryResponse(
            success=True,
            message="Webhook retry task completed successfully",
            stripe=WebhookRetryStats(**stats["stripe"]),
            clerk=WebhookRetryStats(**stats["clerk"]),
            total=WebhookRetryStats(**stats["total"]),
        )

    except Exception as e:
        logger.error(f"[Admin] Webhook retry task failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to execute webhook retry task")


@router.get("/failed", response_model=FailedWebhooksResponse)
@limiter.limit("30/minute")
async def get_failed_webhooks(
    request: Request,
    limit: int = Query(50, ge=1, le=100, description="Max webhooks per type"),
    admin: dict = Depends(require_admin),
):
    """
    Get list of failed webhook events.

    Returns failed webhooks for both Stripe and Clerk that are still
    eligible for retry (not exceeded max retries or age limit).

    **Parameters**:
    - limit: Maximum number of events to return per type (default: 50, max: 100)

    **Security**: Admin role required

    **Rate Limit**: 30 requests per minute

    Returns:
        FailedWebhooksResponse with lists of failed events

    Example Response:
        {
            "stripe_events": [
                {
                    "id": "uuid",
                    "event_id": "evt_123",
                    "event_type": "checkout.session.completed",
                    "retry_count": 2,
                    "error_message": "HTTPException: User not found",
                    "created_at": "2026-01-11T12:00:00Z"
                }
            ],
            "clerk_events": [],
            "total_count": 1
        }
    """
    try:
        db = await get_async_db_client()
        webhook_repo = SupabaseWebhookRepository(db)

        # Get failed events
        from config import WEBHOOK_MAX_RETRIES, WEBHOOK_MAX_RETRY_AGE_HOURS

        stripe_failed = await webhook_repo.get_failed_stripe_webhooks(
            max_retry_count=WEBHOOK_MAX_RETRIES,
            hours_since_created=WEBHOOK_MAX_RETRY_AGE_HOURS,
            limit=limit,
        )

        clerk_failed = await webhook_repo.get_failed_clerk_webhooks(
            max_retry_count=WEBHOOK_MAX_RETRIES,
            hours_since_created=WEBHOOK_MAX_RETRY_AGE_HOURS,
            limit=limit,
        )

        # Convert to response models
        stripe_entries = [
            FailedWebhookEntry(
                id=event["id"],
                event_id=event["event_id"],
                event_type=event["event_type"],
                retry_count=event["retry_count"],
                error_message=event.get("error_message"),
                created_at=event["created_at"],
            )
            for event in stripe_failed
        ]

        clerk_entries = [
            FailedWebhookEntry(
                id=event["id"],
                event_id=event["event_id"],
                event_type=event["event_type"],
                retry_count=event["retry_count"],
                error_message=event.get("error_message"),
                created_at=event["created_at"],
            )
            for event in clerk_failed
        ]

        logger.info(
            f"[Admin {admin.get('id')}] Retrieved failed webhooks: "
            f"{len(stripe_entries)} Stripe, {len(clerk_entries)} Clerk"
        )

        return FailedWebhooksResponse(
            stripe_events=stripe_entries,
            clerk_events=clerk_entries,
            total_count=len(stripe_entries) + len(clerk_entries),
        )

    except Exception as e:
        logger.error(f"[Admin] Failed to retrieve failed webhooks: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve failed webhook events")
