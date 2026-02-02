"""
Webhook Retry Admin API

Admin endpoints for managing webhook retry logic (P3-022).

@module api.admin.webhooks_retry
@version 1.1.0 (Container-based DI)

Changes in v1.1.0:
- WEBHOOK-ARCH-1: Migrated to Container-based dependency injection
- WEBHOOK-ARCH-2: Removed direct repository imports from API layer
- Architecture: API → Container → Service → Repository (Strict DIP)

Endpoints:
- POST /api/v2/admin/webhooks/retry - Manually trigger webhook retry task
- GET /api/v2/admin/webhooks/failed - View failed webhook events
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel, Field

from dependencies import require_admin
from infrastructure.rate_limiter import limiter

# v1.1.0: Container-based DI
# WHY: API layer should not know about concrete repository implementations
from container import get_container

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
    total: WebhookRetryStats = Field(..., description="Combined stats")


class FailedWebhookEntry(BaseModel):
    """Single failed webhook entry."""
    id: str = Field(..., description="Webhook event UUID")
    event_id: str = Field(..., description="External event ID (Stripe)")
    event_type: str = Field(..., description="Event type")
    retry_count: int = Field(..., description="Number of retry attempts")
    error_message: Optional[str] = Field(None, description="Last error message")
    created_at: str = Field(..., description="Event creation timestamp")


class FailedWebhooksResponse(BaseModel):
    """Response for failed webhooks list."""
    stripe_events: list[FailedWebhookEntry] = Field(..., description="Failed Stripe webhooks")
    total_count: int = Field(..., description="Total number of failed webhooks")


# ==========================================
# Dependency Injection (v1.1.0: Container-based)
# ==========================================

async def get_webhook_retry_service():
    """
    Get WebhookRetryService from Container.

    WHY Container-based DI?
    1. Decouples API layer from infrastructure implementations
    2. Enables easy testing with mock services
    3. Centralizes complex service construction (4 repos + 2 services)
    4. Supports future provider switches
    """
    container = get_container()
    return await container.get_webhook_retry_service()


async def get_webhook_repository():
    """
    Get WebhookRepository from Container for query operations.

    Used for get_failed_webhooks endpoint which only needs read access.

    WHY separate from get_webhook_retry_service?
    - This endpoint only needs read access (list failed webhooks)
    - Avoids overhead of constructing full retry service with Stripe service
    """
    container = get_container()
    return await container.get_webhook_repository()


# ==========================================
# Endpoints
# ==========================================

@router.post("/retry", response_model=WebhookRetryResponse)
@limiter.limit("10/hour")  # Strict rate limit - this is expensive operation
async def retry_failed_webhooks(
    request: Request,
    admin: dict = Depends(require_admin),
    retry_service=Depends(get_webhook_retry_service),
):
    """
    Manually trigger webhook retry task.

    v1.1.0: Refactored to use Container-based DI.

    Reprocesses all failed webhook events that are eligible for retry.
    """
    try:
        logger.info(f"[Admin {admin.get('id')}] Triggered webhook retry task")

        # Run retry task
        stats = await retry_service.retry_all_failed_webhooks()

        return WebhookRetryResponse(
            success=True,
            message="Webhook retry task completed successfully",
            stripe=WebhookRetryStats(**stats["stripe"]),
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
    webhook_repo=Depends(get_webhook_repository),
):
    """
    Get list of failed webhook events.

    v1.1.0: Refactored to use Container-based DI.

    Returns failed Stripe webhooks that are still eligible for retry
    (not exceeded max retries or age limit).
    """
    try:
        from config import WEBHOOK_MAX_RETRIES, WEBHOOK_MAX_RETRY_AGE_HOURS

        stripe_failed = await webhook_repo.get_failed_stripe_webhooks(
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

        logger.info(
            f"[Admin {admin.get('id')}] Retrieved failed webhooks: "
            f"{len(stripe_entries)} Stripe"
        )

        return FailedWebhooksResponse(
            stripe_events=stripe_entries,
            total_count=len(stripe_entries),
        )

    except Exception as e:
        logger.error(f"[Admin] Failed to retrieve failed webhooks: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve failed webhook events")
