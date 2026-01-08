"""
Campaigns API - Marketing campaigns endpoints (v2).

@module api.user.campaigns
@version 2.1.0

Changes:
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
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from dependencies import optional_user, get_current_user
from infrastructure.repositories.credit_repository import SupabaseCreditRepository
from infrastructure.rate_limiter import limiter
from core.database import get_supabase_client, get_database_client

supabase = get_supabase_client()

logger = logging.getLogger(__name__)

# ==========================================
# Constants
# ==========================================

# Valid notification channels
VALID_NOTIFICATION_CHANNELS = {"banner", "modal", "toast", "personal_message"}

# Valid campaign types
VALID_CAMPAIGN_TYPES = {"credits_gift", "credits_discount", "credits_bonus"}

# Maximum credit amount for validation
MAX_CREDIT_AMOUNT = 10000

# UUID regex pattern for validation
UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)

router = APIRouter(prefix="/campaigns", tags=["user-campaigns-v2"])


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
) -> ActiveCampaignsResponse:
    """
    Get all active campaigns visible to the current user.

    Returns campaigns filtered by:
    1. Active status and within time range
    2. Target audience eligibility
    3. Claim status
    """
    now = datetime.now(timezone.utc)

    # v2.1.0: CP-P0-1 - Fix time range query
    # Correct logic: start_at <= now AND end_at > now (strictly greater)
    result = supabase.table("campaigns").select("*").eq(
        "status", "active",
    ).eq("is_active", True).lte(
        "start_at", now.isoformat(),  # Campaign has started
    ).gt(
        "end_at", now.isoformat(),  # Campaign has NOT ended (strict >)
    ).execute()

    if not result.data:
        return ActiveCampaignsResponse(
            campaigns=[],
            notifications=NotificationsResponse(),
        )

    # Batch fetch user claims and dismissals to avoid N+1 queries
    campaign_ids = [c["id"] for c in result.data]
    claimed_campaigns: set = set()
    dismissed_map: Dict[str, List[str]] = {}  # campaign_id -> list of dismissed channels

    if user:
        claimed_campaigns, dismissed_map = _batch_get_user_campaign_status(
            campaign_ids, user["id"]
        )

    campaigns = []
    notifications = NotificationsResponse()

    for campaign in result.data:
        if not _check_target_eligibility(campaign, user):
            continue

        has_claimed = campaign["id"] in claimed_campaigns
        dismissed_channels = dismissed_map.get(campaign["id"], [])
        can_claim = not has_claimed and _check_usage_limit(campaign)

        campaign_data = {
            **campaign,
            "has_claimed": has_claimed,
            "can_claim": can_claim,
        }
        campaigns.append(campaign_data)

        # Build notifications for non-dismissed channels
        # v2.1.0: CP-HIGH-5 - Validate notification channels
        for channel in campaign.get("notification_channels", []):
            # Skip invalid channels
            if channel not in VALID_NOTIFICATION_CHANNELS:
                logger.warning(f"[Campaigns] Invalid notification channel: {channel}")
                continue

            if channel in dismissed_channels or channel == "personal_message":
                continue

            notification = _build_notification(campaign, channel, can_claim=can_claim)

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
) -> ClaimResponse:
    """
    Claim a campaign reward.

    Validates eligibility and grants reward based on campaign type.

    **Idempotency**: Protected by UNIQUE constraint on (campaign_id, user_id).
    Duplicate claims return 400 error.

    **Atomicity**: Credits are granted atomically with the claim record.
    If credit granting fails, the claim record is rolled back.
    """
    # v2.1.0: CP-P0-3 - Validate campaign_id format
    if not UUID_PATTERN.match(campaign_id):
        raise HTTPException(400, "Invalid campaign ID format")

    result = supabase.table("campaigns").select("*").eq(
        "id", campaign_id,
    ).execute()

    if not result.data:
        raise HTTPException(404, "Campaign not found")

    campaign = result.data[0]

    if campaign["status"] != "active" or not campaign["is_active"]:
        raise HTTPException(400, "Campaign is not active")

    # Validate time range
    now = datetime.now(timezone.utc)
    start_at = _parse_iso_datetime(campaign["start_at"])
    end_at = _parse_iso_datetime(campaign["end_at"])

    if not start_at or not end_at:
        logger.error(f"[Campaigns] Invalid datetime in campaign {campaign_id}")
        raise HTTPException(500, "Campaign configuration error")

    if now < start_at:
        raise HTTPException(400, "Campaign has not started yet")
    if now >= end_at:  # v2.1.0: Use >= for consistency with query
        raise HTTPException(400, "Campaign has ended")

    if not _check_target_eligibility(campaign, user):
        raise HTTPException(403, "You are not eligible for this campaign")

    # v2.1.0: CP-P0-2 - Remove redundant check, rely on UNIQUE constraint
    # The INSERT with UNIQUE constraint is the authoritative check

    # v2.1.0: CP-HIGH-2 - Handle None usage_count defensively
    usage_limit = campaign.get("usage_limit")
    usage_count = campaign.get("usage_count") or 0
    if usage_limit and usage_count >= usage_limit:
        raise HTTPException(400, "Campaign usage limit reached")

    # v2.1.0: CP-HIGH-3 - Validate credits amount
    credits_received = 0
    config = campaign.get("config", {})
    campaign_type = campaign.get("type")

    # Validate campaign type
    if campaign_type not in VALID_CAMPAIGN_TYPES:
        logger.error(f"[Campaigns] Unknown campaign type: {campaign_type}")
        raise HTTPException(500, "Campaign configuration error")

    if campaign_type == "credits_gift":
        raw_amount = config.get("amount", 0)
        credits_received = _validate_credit_amount(raw_amount)
        if credits_received is None:
            logger.error(f"[Campaigns] Invalid credit amount in campaign {campaign_id}: {raw_amount}")
            raise HTTPException(500, "Campaign configuration error")

    # Insert claim record FIRST (uses UNIQUE constraint to prevent race condition)
    try:
        supabase.table("campaign_claims").insert({
            "campaign_id": campaign_id,
            "user_id": user["id"],
            "credits_received": credits_received,
        }).execute()
    except Exception as e:
        # v2.1.0: CP-P0-4 - Don't expose internal error details
        error_str = str(e).lower()
        if "duplicate" in error_str or "unique" in error_str:
            raise HTTPException(400, "You have already claimed this campaign")
        logger.error(f"[Campaigns] Failed to record claim: {e}")
        raise HTTPException(500, "Failed to process claim. Please try again.")

    # Now safely grant credits (claim is already recorded, no race condition)
    try:
        if credits_received > 0:
            credit_repo = SupabaseCreditRepository(get_database_client())
            await credit_repo.add_credits_permanent(
                user["id"],
                credits_received,
                f"Campaign reward: {campaign['name']}",
                "campaign_gift",
            )
    except Exception as e:
        # Credit granting failed - remove the claim record for retry
        # v2.1.0: CP-P0-4 - Sanitize log message
        logger.error(f"[Campaigns] Credit grant failed for campaign {campaign_id}")
        supabase.table("campaign_claims").delete().eq(
            "campaign_id", campaign_id
        ).eq("user_id", user["id"]).execute()
        raise HTTPException(500, "Failed to grant credits. Please try again.")

    # Atomic increment usage counter
    try:
        result = supabase.rpc("increment_campaign_usage", {
            "p_campaign_id": campaign_id,
        }).execute()

        if not result.data:
            logger.warning(f"[Campaigns] Usage increment returned no data for {campaign_id}")
    except Exception as e:
        # Log but don't fail - claim is already recorded
        logger.warning(f"[Campaigns] Failed to increment usage_count for {campaign_id}")

    # v2.1.0: CP-MEDIUM-2 - Audit logging
    logger.info(
        f"[Campaigns] CLAIM_SUCCESS campaign={campaign_id} credits={credits_received}"
    )

    message = f"You received {credits_received} credits!" if credits_received > 0 else "Offer claimed successfully!"
    return ClaimResponse(
        success=True,
        credits_received=credits_received,
        message=message,
    )


@router.post("/{campaign_id}/dismiss")
@limiter.limit("30/minute")  # v2.1.0: CP-MEDIUM-1 - Rate limiting
async def dismiss_notification(
    request: Request,
    campaign_id: str,
    req: DismissRequest,
    user: dict = Depends(get_current_user),
) -> DismissResponse:
    """Dismiss a campaign notification for a specific channel."""
    # v2.1.0: CP-P0-3 - Validate campaign_id format
    if not UUID_PATTERN.match(campaign_id):
        raise HTTPException(400, "Invalid campaign ID format")

    supabase.table("campaign_dismissals").upsert({
        "campaign_id": campaign_id,
        "user_id": user["id"],
        "channel": req.channel,
        "dismissed_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="campaign_id,user_id,channel").execute()

    return DismissResponse(success=True)


# ==========================================
# Helper Functions
# ==========================================

def _check_target_eligibility(campaign: dict, user: Optional[dict]) -> bool:
    """Check if user matches the campaign's target audience."""
    target_type = campaign.get("target_type", "all")
    target_config = campaign.get("target_config", {})

    if target_type == "all":
        return True

    if not user:
        return False

    if target_type == "subscription":
        user_tier = user.get("tier", "free")
        allowed_tiers = target_config.get("tiers", [])
        return user_tier in allowed_tiers

    elif target_type == "users":
        allowed_users = target_config.get("user_ids", [])
        return user["id"] in allowed_users

    elif target_type == "new_users":
        days = target_config.get("days_since_signup", 7)
        created_at = user.get("created_at")
        if not created_at:
            return False
        try:
            signup_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            return (now - signup_date).days <= days
        except Exception:
            return False

    elif target_type == "inactive_users":
        days = target_config.get("days_inactive", 30)
        last_login = user.get("last_login_at")
        if not last_login:
            return True  # Never logged in = inactive
        try:
            login_date = datetime.fromisoformat(last_login.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            return (now - login_date).days >= days
        except Exception:
            return False

    return False


def _batch_get_user_campaign_status(
    campaign_ids: List[str], user_id: str
) -> tuple[set, Dict[str, List[str]]]:
    """
    Batch fetch user's claim and dismissal status for multiple campaigns.

    Returns:
        tuple: (claimed_campaign_ids: set, dismissed_map: dict[campaign_id, list[channels]])
    """
    claimed_campaigns: set = set()
    dismissed_map: Dict[str, List[str]] = {}

    if not campaign_ids:
        return claimed_campaigns, dismissed_map

    # Batch query claims
    try:
        claims_result = supabase.table("campaign_claims").select(
            "campaign_id"
        ).eq("user_id", user_id).in_("campaign_id", campaign_ids).execute()

        claimed_campaigns = {c["campaign_id"] for c in claims_result.data}
    except Exception as e:
        logger.warning(f"[Campaigns] Failed to batch fetch claims: {e}")

    # Batch query dismissals
    try:
        dismissals_result = supabase.table("campaign_dismissals").select(
            "campaign_id, channel"
        ).eq("user_id", user_id).in_("campaign_id", campaign_ids).execute()

        for d in dismissals_result.data:
            campaign_id = d["campaign_id"]
            if campaign_id not in dismissed_map:
                dismissed_map[campaign_id] = []
            dismissed_map[campaign_id].append(d["channel"])
    except Exception as e:
        logger.warning(f"[Campaigns] Failed to batch fetch dismissals: {e}")

    return claimed_campaigns, dismissed_map


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    """
    Parse ISO datetime string to datetime object.

    v2.1.0: CP-HIGH-4 - Centralized datetime parsing for consistency.

    Args:
        value: ISO format datetime string (may end with Z or +00:00)

    Returns:
        datetime object with UTC timezone, or None if parsing fails
    """
    if not value:
        return None
    try:
        # Handle both 'Z' suffix and '+00:00' format
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except (ValueError, TypeError):
        return None


def _validate_credit_amount(amount: Any) -> Optional[int]:
    """
    Validate credit amount is within acceptable range.

    v2.1.0: CP-HIGH-3 - Validate config.amount to prevent abuse.

    Args:
        amount: Raw amount value from config

    Returns:
        Validated integer amount, or None if invalid
    """
    try:
        value = int(amount)
        if value < 0 or value > MAX_CREDIT_AMOUNT:
            return None
        return value
    except (ValueError, TypeError):
        return None


def _check_usage_limit(campaign: dict) -> bool:
    """Check if campaign has remaining usage capacity."""
    usage_limit = campaign.get("usage_limit")
    if usage_limit is None:
        return True
    return campaign.get("usage_count", 0) < usage_limit


def _build_notification(campaign: dict, channel: str, can_claim: bool = True) -> NotificationData:
    """Build notification data structure for a channel."""
    config = campaign.get("notification_config", {})

    return NotificationData(
        campaign_id=campaign["id"],
        campaign_type=campaign["type"],
        channel=channel,
        title=config.get("title", campaign["name"]),
        message=config.get("message", campaign.get("description", "")),
        cta_text=config.get("cta_text", "Learn More"),
        cta_url=config.get("cta_url", "/pricing"),
        show_once=config.get("show_once", False),
        can_claim=can_claim,
    )
