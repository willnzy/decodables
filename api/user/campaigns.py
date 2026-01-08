"""
Campaigns API - Marketing campaigns endpoints (v2).

@module api.user.campaigns
@version 2.2.0

Changes:
- v2.2.0: DDD architecture migration
  - CP-MEDIUM-3: Migrate to use CampaignService and Repository
  - API layer now uses dependency injection for CampaignService
  - Removed direct supabase access from API layer

- v2.1.1: Code quality improvements
  - CP-LOW-3: Unified datetime parsing using _parse_iso_datetime()

- v2.1.0: Security fixes
  - CP-P0-1: Fix time range query logic (gte → gt for end_at)
  - CP-P0-3: Add UUID validation for campaign_id
  - CP-P0-4: Sanitize error messages and log output
  - CP-HIGH-2: Handle None usage_count defensively
  - CP-HIGH-3: Validate config.amount range
  - CP-HIGH-5: Validate notification channels
  - CP-MEDIUM-1: Add rate limiting
  - CP-MEDIUM-2: Add audit logging for claims
  - CP-LOW-1: Remove unused helper functions

Endpoints:
- GET /api/v2/user/campaigns/active - Get active campaigns
- POST /api/v2/user/campaigns/{id}/claim - Claim campaign reward
- POST /api/v2/user/campaigns/{id}/dismiss - Dismiss notification
"""

import logging
import re
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from dependencies import optional_user, get_current_user
from infrastructure.repositories.credit_repository import SupabaseCreditRepository
from infrastructure.repositories.campaign_repository import SupabaseCampaignRepository
from infrastructure.rate_limiter import limiter
from core.database import get_supabase_client, get_database_client
from domains.marketing import CampaignService, ClaimResult, CampaignWithStatus
from domains.marketing.repository import CampaignData

logger = logging.getLogger(__name__)

# ==========================================
# Constants
# ==========================================

# Valid notification channels (for building notification responses)
VALID_NOTIFICATION_CHANNELS = {"banner", "modal", "toast", "personal_message"}

# UUID regex pattern for validation
UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)

router = APIRouter(prefix="/campaigns", tags=["user-campaigns-v2"])


# ==========================================
# Dependency Injection
# ==========================================

def get_campaign_service() -> CampaignService:
    """
    Dependency injection factory for CampaignService.

    Creates a CampaignService with the SupabaseCampaignRepository.
    """
    supabase = get_supabase_client()
    campaign_repo = SupabaseCampaignRepository(supabase)
    return CampaignService(campaign_repo)


async def get_grant_credits_fn(user_id: str, amount: int, description: str) -> None:
    """
    Helper function to grant credits via billing domain.

    This bridges the campaign service to the credit repository.
    """
    credit_repo = SupabaseCreditRepository(get_database_client())
    await credit_repo.add_credits_permanent(
        user_id,
        amount,
        description,
        "campaign_gift",
    )


# ==========================================
# Request/Response Models
# ==========================================

class DismissRequest(BaseModel):
    """Dismiss notification request."""
    channel: str = Field(..., pattern="^(modal|toast|banner)$")


class NotificationData(BaseModel):
    """Notification data."""
    campaign_id: str
    campaign_type: str
    channel: str
    title: str
    message: str
    cta_text: str
    cta_url: str
    show_once: bool
    can_claim: bool


class NotificationsResponse(BaseModel):
    """Notifications grouped by channel."""
    modal: Optional[NotificationData] = None
    toast: Optional[NotificationData] = None
    banner: List[NotificationData] = []


class CampaignResponse(BaseModel):
    """Campaign data with user-specific info."""
    id: str
    name: str
    type: str
    status: str
    has_claimed: bool
    can_claim: bool


class ActiveCampaignsResponse(BaseModel):
    """Active campaigns response."""
    campaigns: List[Dict[str, Any]]
    notifications: NotificationsResponse


class ClaimResponse(BaseModel):
    """Claim response."""
    success: bool
    credits_received: int
    message: str


class DismissResponse(BaseModel):
    """Dismiss response."""
    success: bool


# ==========================================
# Endpoints
# ==========================================

@router.get("/active")
async def get_active_campaigns(
    user: Optional[dict] = Depends(optional_user),
    campaign_service: CampaignService = Depends(get_campaign_service),
) -> ActiveCampaignsResponse:
    """
    Get all active campaigns visible to the current user.

    Returns campaigns filtered by:
    1. Active status and within time range
    2. Target audience eligibility
    3. Claim status

    v2.2.0: Migrated to use CampaignService (DDD architecture)
    """
    # Use CampaignService to get campaigns with status
    campaigns_with_status, dismissed_map = await campaign_service.get_active_campaigns_for_user(user)

    if not campaigns_with_status:
        return ActiveCampaignsResponse(
            campaigns=[],
            notifications=NotificationsResponse(),
        )

    campaigns = []
    notifications = NotificationsResponse()

    for cws in campaigns_with_status:
        campaign = cws.campaign
        dismissed_channels = dismissed_map.get(campaign.id, [])

        # Convert CampaignData to dict for response
        campaign_data = {
            "id": campaign.id,
            "name": campaign.name,
            "description": campaign.description,
            "type": campaign.type,
            "config": campaign.config,
            "target_type": campaign.target_type,
            "target_config": campaign.target_config,
            "notification_channels": campaign.notification_channels,
            "notification_config": campaign.notification_config,
            "start_at": campaign.start_at.isoformat(),
            "end_at": campaign.end_at.isoformat(),
            "usage_limit": campaign.usage_limit,
            "usage_count": campaign.usage_count,
            "status": campaign.status,
            "is_active": campaign.is_active,
            "has_claimed": cws.has_claimed,
            "can_claim": cws.can_claim,
        }
        campaigns.append(campaign_data)

        # Build notifications for non-dismissed channels
        for channel in campaign.notification_channels:
            # Skip invalid channels
            if channel not in VALID_NOTIFICATION_CHANNELS:
                logger.warning(f"[Campaigns] Invalid notification channel: {channel}")
                continue

            if channel in dismissed_channels or channel == "personal_message":
                continue

            notification = _build_notification_from_data(campaign, channel, can_claim=cws.can_claim)

            if channel == "banner":
                notifications.banner.append(notification)
            elif channel == "modal" and notifications.modal is None:
                notifications.modal = notification
            elif channel == "toast" and notifications.toast is None:
                notifications.toast = notification

    return ActiveCampaignsResponse(
        campaigns=campaigns,
        notifications=notifications,
    )


@router.post("/{campaign_id}/claim")
@limiter.limit("10/minute")  # v2.1.0: CP-MEDIUM-1 - Rate limiting
async def claim_campaign(
    request: Request,
    campaign_id: str,
    user: dict = Depends(get_current_user),
    campaign_service: CampaignService = Depends(get_campaign_service),
) -> ClaimResponse:
    """
    Claim a campaign reward.

    Validates eligibility and grants reward based on campaign type.

    **Idempotency**: Protected by UNIQUE constraint on (campaign_id, user_id).
    Duplicate claims return 400 error.

    **Atomicity**: Credits are granted atomically with the claim record.
    If credit granting fails, the claim record is rolled back.

    v2.2.0: Migrated to use CampaignService (DDD architecture)
    """
    # v2.1.0: CP-P0-3 - Validate campaign_id format
    if not UUID_PATTERN.match(campaign_id):
        raise HTTPException(400, "Invalid campaign ID format")

    # Use CampaignService to claim the campaign
    result: ClaimResult = await campaign_service.claim_campaign(
        campaign_id=campaign_id,
        user=user,
        grant_credits_fn=get_grant_credits_fn,
    )

    if not result.success:
        # Map error codes to HTTP status codes
        error_code = result.error_code
        if error_code == "NOT_FOUND":
            raise HTTPException(404, result.message)
        elif error_code == "NOT_ELIGIBLE":
            raise HTTPException(403, result.message)
        elif error_code in ("INACTIVE", "NOT_STARTED", "ENDED", "LIMIT_REACHED", "ALREADY_CLAIMED"):
            raise HTTPException(400, result.message)
        elif error_code in ("CONFIG_ERROR", "CREDIT_FAILED"):
            raise HTTPException(500, result.message)
        else:
            raise HTTPException(500, result.message)

    return ClaimResponse(
        success=True,
        credits_received=result.credits_received,
        message=result.message,
    )


@router.post("/{campaign_id}/dismiss")
@limiter.limit("30/minute")  # v2.1.0: CP-MEDIUM-1 - Rate limiting
async def dismiss_notification(
    request: Request,
    campaign_id: str,
    req: DismissRequest,
    user: dict = Depends(get_current_user),
    campaign_service: CampaignService = Depends(get_campaign_service),
) -> DismissResponse:
    """
    Dismiss a campaign notification for a specific channel.

    v2.2.0: Migrated to use CampaignService (DDD architecture)
    """
    # v2.1.0: CP-P0-3 - Validate campaign_id format
    if not UUID_PATTERN.match(campaign_id):
        raise HTTPException(400, "Invalid campaign ID format")

    # Validate notification channel (already validated by pydantic pattern)
    if not campaign_service.is_valid_notification_channel(req.channel):
        raise HTTPException(400, "Invalid notification channel")

    await campaign_service.dismiss_notification(campaign_id, user["id"], req.channel)

    return DismissResponse(success=True)


# ==========================================
# Helper Functions
# ==========================================

# v2.2.0: Removed legacy helper functions that are now in CampaignService:
# - _check_target_eligibility() → CampaignService._check_target_eligibility()
# - _batch_get_user_campaign_status() → CampaignRepository.get_user_campaign_status()
# - _parse_iso_datetime() → CampaignService uses datetime.fromisoformat()
# - _validate_credit_amount() → CampaignService._validate_credit_amount()
# - _check_usage_limit() → CampaignService._check_usage_limit()


def _build_notification_from_data(campaign: CampaignData, channel: str, can_claim: bool = True) -> NotificationData:
    """
    Build notification data structure for a channel from CampaignData.

    v2.2.0: New helper for CampaignData (replaces dict-based _build_notification)
    """
    config = campaign.notification_config

    return NotificationData(
        campaign_id=campaign.id,
        campaign_type=campaign.type,
        channel=channel,
        title=config.get("title", campaign.name),
        message=config.get("message", campaign.description or ""),
        cta_text=config.get("cta_text", "Learn More"),
        cta_url=config.get("cta_url", "/pricing"),
        show_once=config.get("show_once", False),
        can_claim=can_claim,
    )
