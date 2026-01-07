"""
Campaigns API - Marketing campaigns endpoints (v2).

@module api.user.campaigns
@version 2.0.0

Endpoints:
- GET /api/v2/user/campaigns/active - Get active campaigns
- POST /api/v2/user/campaigns/{id}/claim - Claim campaign reward
- POST /api/v2/user/campaigns/{id}/dismiss - Dismiss notification
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from dependencies import optional_user, get_current_user
from infrastructure.repositories.credit_repository import SupabaseCreditRepository
from core.database import get_supabase_client, get_database_client

supabase = get_supabase_client()

logger = logging.getLogger(__name__)

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

    result = supabase.table("campaigns").select("*").eq(
        "status", "active",
    ).eq("is_active", True).lte(
        "start_at", now.isoformat(),
    ).gte(
        "end_at", now.isoformat(),
    ).execute()

    if not result.data:
        return ActiveCampaignsResponse(
            campaigns=[],
            notifications=NotificationsResponse(),
        )

    campaigns = []
    notifications = NotificationsResponse()

    for campaign in result.data:
        if not _check_target_eligibility(campaign, user):
            continue

        has_claimed = False
        dismissed_channels: List[str] = []

        if user:
            has_claimed = _check_has_claimed(campaign["id"], user["id"])
            dismissed_channels = _get_dismissed_channels(campaign["id"], user["id"])

        can_claim = not has_claimed and _check_usage_limit(campaign)

        campaign_data = {
            **campaign,
            "has_claimed": has_claimed,
            "can_claim": can_claim,
        }
        campaigns.append(campaign_data)

        # Build notifications for non-dismissed channels
        for channel in campaign.get("notification_channels", []):
            if channel in dismissed_channels or channel == "personal_message":
                continue

            notification = _build_notification(campaign, channel)

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
async def claim_campaign(
    campaign_id: str,
    user: dict = Depends(get_current_user),
) -> ClaimResponse:
    """
    Claim a campaign reward.

    Validates eligibility and grants reward based on campaign type.
    """
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
    start_at = datetime.fromisoformat(campaign["start_at"].replace("Z", "+00:00"))
    end_at = datetime.fromisoformat(campaign["end_at"].replace("Z", "+00:00"))

    if now < start_at:
        raise HTTPException(400, "Campaign has not started yet")
    if now > end_at:
        raise HTTPException(400, "Campaign has ended")

    if not _check_target_eligibility(campaign, user):
        raise HTTPException(403, "You are not eligible for this campaign")

    # Check for duplicate claim
    existing = supabase.table("campaign_claims").select("id").eq(
        "campaign_id", campaign_id,
    ).eq("user_id", user["id"]).execute()

    if existing.data:
        raise HTTPException(400, "You have already claimed this campaign")

    # Check usage limit
    usage_limit = campaign.get("usage_limit")
    if usage_limit and campaign["usage_count"] >= usage_limit:
        raise HTTPException(400, "Campaign usage limit reached")

    # Process claim
    credits_received = 0
    config = campaign.get("config", {})

    if campaign["type"] == "credits_gift":
        credits_received = config.get("amount", 0)
        if credits_received > 0:
            credit_repo = SupabaseCreditRepository(get_database_client())
            await credit_repo.add_credits_permanent(
                user["id"],
                credits_received,
                f"Campaign reward: {campaign['name']}",
                "campaign_gift",
            )

    # Record the claim
    supabase.table("campaign_claims").insert({
        "campaign_id": campaign_id,
        "user_id": user["id"],
        "credits_received": credits_received,
    }).execute()

    # Increment usage counter
    supabase.table("campaigns").update({
        "usage_count": campaign["usage_count"] + 1,
    }).eq("id", campaign_id).execute()

    message = f"You received {credits_received} credits!" if credits_received > 0 else "Offer claimed successfully!"
    return ClaimResponse(
        success=True,
        credits_received=credits_received,
        message=message,
    )


@router.post("/{campaign_id}/dismiss")
async def dismiss_notification(
    campaign_id: str,
    req: DismissRequest,
    user: dict = Depends(get_current_user),
) -> DismissResponse:
    """Dismiss a campaign notification for a specific channel."""
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


def _check_has_claimed(campaign_id: str, user_id: str) -> bool:
    """Check if user has already claimed this campaign."""
    result = supabase.table("campaign_claims").select("id").eq(
        "campaign_id", campaign_id,
    ).eq("user_id", user_id).execute()
    return len(result.data) > 0


def _get_dismissed_channels(campaign_id: str, user_id: str) -> List[str]:
    """Get list of dismissed notification channels."""
    result = supabase.table("campaign_dismissals").select("channel").eq(
        "campaign_id", campaign_id,
    ).eq("user_id", user_id).execute()
    return [d["channel"] for d in result.data]


def _check_usage_limit(campaign: dict) -> bool:
    """Check if campaign has remaining usage capacity."""
    usage_limit = campaign.get("usage_limit")
    if usage_limit is None:
        return True
    return campaign.get("usage_count", 0) < usage_limit


def _build_notification(campaign: dict, channel: str) -> NotificationData:
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
        can_claim=True,
    )
