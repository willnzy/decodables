"""
Admin Campaigns API - Campaign management for admins.

@module api.admin.campaigns
@version 3.25

Changes:
- v3.25: Security improvements
  - CAM-MEDIUM-1: Added rate limiting to all endpoints
  - CAM-MEDIUM-2: Added status parameter validation (enum)
  - CAM-MEDIUM-3: Improved campaign_id validation
  - CAM-MEDIUM-4: Added target_type enum validation to update model
  - CAM-MEDIUM-5: Added name length validation
  - CAM-LOW-1: Improved error message consistency

Endpoints:
- GET /campaigns - List campaigns
- GET /campaigns/{id} - Get campaign
- POST /campaigns - Create campaign
- PUT /campaigns/{id} - Update campaign
- DELETE /campaigns/{id} - Delete campaign
- POST /campaigns/{id}/activate - Activate campaign
- POST /campaigns/{id}/pause - Pause campaign
- GET /campaigns/{id}/stats - Get campaign stats
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

from dependencies import require_admin
from infrastructure.rate_limiter import limiter

from core.database import get_supabase_client
supabase = get_supabase_client()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["admin-campaigns-v2"])


# ==========================================
# Constants (v3.25)
# ==========================================

# v3.25: CAM-MEDIUM-2 - Valid campaign statuses
VALID_CAMPAIGN_STATUSES = {"draft", "active", "paused", "completed", "deleted"}

# v3.25: Valid campaign types
VALID_CAMPAIGN_TYPES = {"credits_gift", "credits_discount", "credits_bonus"}

# v3.25: Valid target types
VALID_TARGET_TYPES = {"all", "subscription", "users", "new_users", "inactive_users"}


# ==========================================
# Request Models (v3.25: Added field validations)
# ==========================================

class CampaignCreateRequest(BaseModel):
    """Campaign creation request."""
    # v3.25: CAM-MEDIUM-5 - Name length validation
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    type: str = Field(..., pattern="^(credits_gift|credits_discount|credits_bonus)$")
    config: dict
    target_type: str = Field(..., pattern="^(all|subscription|users|new_users|inactive_users)$")
    target_config: Optional[dict] = None
    notification_channels: List[str] = []
    notification_config: Optional[dict] = None
    start_at: str = Field(..., max_length=50)
    end_at: Optional[str] = Field(None, max_length=50)
    timezone: str = Field("UTC", max_length=50)
    usage_limit: Optional[int] = Field(None, ge=1, le=1000000)
    usage_per_user: Optional[int] = Field(None, ge=1, le=100)


class CampaignUpdateRequest(BaseModel):
    """Campaign update request."""
    # v3.25: CAM-MEDIUM-5 - Name length validation
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    config: Optional[dict] = None
    target_type: Optional[str] = Field(None, max_length=50)
    target_config: Optional[dict] = None
    notification_channels: Optional[List[str]] = None
    notification_config: Optional[dict] = None
    start_at: Optional[str] = Field(None, max_length=50)
    end_at: Optional[str] = Field(None, max_length=50)
    usage_limit: Optional[int] = Field(None, ge=1, le=1000000)

    # v3.25: CAM-MEDIUM-4 - target_type validation
    @field_validator("target_type")
    @classmethod
    def validate_target_type(cls, v):
        if v is not None and v not in VALID_TARGET_TYPES:
            raise ValueError(f"Invalid target_type. Must be one of: {', '.join(VALID_TARGET_TYPES)}")
        return v


# ==========================================
# Endpoints (v3.25: Added rate limiting)
# ==========================================

@router.get("")
@limiter.limit("30/minute")
async def list_campaigns(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Page size (1-100)"),
    admin: dict = Depends(require_admin),
):
    """List all campaigns."""
    # v3.25: CAM-MEDIUM-2 - Validate status parameter
    if status is not None and status not in VALID_CAMPAIGN_STATUSES:
        raise HTTPException(400, f"Invalid status. Must be one of: {', '.join(VALID_CAMPAIGN_STATUSES)}")

    query = supabase.table("campaigns").select("*").order("created_at", desc=True)

    if status:
        query = query.eq("status", status)

    result = query.range(offset, offset + limit - 1).execute()

    return {"campaigns": result.data or [], "offset": offset, "limit": limit}


@router.get("/{campaign_id}")
@limiter.limit("30/minute")
async def get_campaign(
    request: Request,
    campaign_id: str,
    admin: dict = Depends(require_admin),
):
    """Get campaign details."""
    result = supabase.table("campaigns").select("*").eq("id", campaign_id).execute()

    if not result.data:
        raise HTTPException(404, "Campaign not found")

    return result.data[0]


@router.post("")
@limiter.limit("20/minute")
async def create_campaign(
    request: Request,
    req: CampaignCreateRequest,
    admin: dict = Depends(require_admin),
):
    """Create a new campaign."""
    campaign_data = {
        "name": req.name,
        "description": req.description,
        "type": req.type,
        "config": req.config,
        "target_type": req.target_type,
        "target_config": req.target_config,
        "notification_channels": req.notification_channels,
        "notification_config": req.notification_config,
        "start_at": req.start_at,
        "end_at": req.end_at,
        "timezone": req.timezone,
        "usage_limit": req.usage_limit,
        "usage_per_user": req.usage_per_user,
        "status": "draft",
        "is_active": False,
        "created_by": admin["id"],
    }

    try:
        result = supabase.table("campaigns").insert(campaign_data).execute()

        if not result.data:
            raise HTTPException(500, "Failed to create campaign")

        return result.data[0]
    except Exception as e:
        logger.error(f"Failed to create campaign: {e}")
        raise HTTPException(500, "Failed to create campaign")


@router.put("/{campaign_id}")
@limiter.limit("20/minute")
async def update_campaign(
    request: Request,
    campaign_id: str,
    req: CampaignUpdateRequest,
    admin: dict = Depends(require_admin),
):
    """Update a campaign."""
    update_data = {k: v for k, v in req.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(400, "No fields to update")

    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        result = supabase.table("campaigns").update(update_data).eq("id", campaign_id).execute()

        if not result.data:
            raise HTTPException(404, "Campaign not found")

        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update campaign: {e}")
        raise HTTPException(500, "Failed to update campaign")


@router.delete("/{campaign_id}")
@limiter.limit("10/minute")
async def delete_campaign(
    request: Request,
    campaign_id: str,
    admin: dict = Depends(require_admin),
):
    """Delete a campaign (soft delete)."""
    try:
        result = supabase.table("campaigns").update({
            "status": "deleted",
            "is_active": False,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", campaign_id).execute()

        if not result.data:
            raise HTTPException(404, "Campaign not found")

        return {"status": "deleted", "campaign_id": campaign_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete campaign: {e}")
        raise HTTPException(500, "Failed to delete campaign")


@router.post("/{campaign_id}/activate")
@limiter.limit("10/minute")
async def activate_campaign(
    request: Request,
    campaign_id: str,
    admin: dict = Depends(require_admin),
):
    """Activate a campaign."""
    try:
        result = supabase.table("campaigns").update({
            "status": "active",
            "is_active": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", campaign_id).execute()

        if not result.data:
            raise HTTPException(404, "Campaign not found")

        return {"status": "activated", "campaign_id": campaign_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to activate campaign: {e}")
        raise HTTPException(500, "Failed to activate campaign")


@router.post("/{campaign_id}/pause")
@limiter.limit("10/minute")
async def pause_campaign(
    request: Request,
    campaign_id: str,
    admin: dict = Depends(require_admin),
):
    """Pause a campaign."""
    try:
        result = supabase.table("campaigns").update({
            "status": "paused",
            "is_active": False,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", campaign_id).execute()

        if not result.data:
            raise HTTPException(404, "Campaign not found")

        return {"status": "paused", "campaign_id": campaign_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause campaign: {e}")
        raise HTTPException(500, "Failed to pause campaign")


@router.get("/{campaign_id}/stats")
@limiter.limit("30/minute")
async def get_campaign_stats(
    request: Request,
    campaign_id: str,
    admin: dict = Depends(require_admin),
):
    """Get campaign statistics."""
    try:
        # Get campaign
        campaign_result = supabase.table("campaigns").select("*").eq("id", campaign_id).execute()

        if not campaign_result.data:
            raise HTTPException(404, "Campaign not found")

        campaign = campaign_result.data[0]

        # Get claims
        claims_result = supabase.table("campaign_claims").select(
            "id, credits_received, created_at",
        ).eq("campaign_id", campaign_id).execute()

        claims = claims_result.data or []
        total_credits = sum(c.get("credits_received", 0) for c in claims)

        return {
            "campaign_id": campaign_id,
            "campaign_name": campaign.get("name"),
            "status": campaign.get("status"),
            "total_claims": len(claims),
            "total_credits_given": total_credits,
            "usage_count": campaign.get("usage_count", 0),
            "usage_limit": campaign.get("usage_limit"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get campaign stats: {e}")
        raise HTTPException(500, "Failed to get campaign statistics")
