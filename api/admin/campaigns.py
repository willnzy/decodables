"""
Admin Campaigns API - Campaign management for admins.

@module api.admin.campaigns
@version 2.0.0

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

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from dependencies import require_admin
from services.db_service import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["admin-campaigns-v2"])


# ==========================================
# Request Models
# ==========================================

class CampaignCreateRequest(BaseModel):
    """Campaign creation request."""
    name: str
    description: Optional[str] = None
    type: str = Field(..., pattern="^(credits_gift|credits_discount|credits_bonus)$")
    config: dict
    target_type: str = Field(..., pattern="^(all|subscription|users|new_users|inactive_users)$")
    target_config: Optional[dict] = None
    notification_channels: List[str] = []
    notification_config: Optional[dict] = None
    start_at: str
    end_at: Optional[str] = None
    timezone: str = "UTC"
    usage_limit: Optional[int] = None
    usage_per_user: Optional[int] = None


class CampaignUpdateRequest(BaseModel):
    """Campaign update request."""
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[dict] = None
    target_type: Optional[str] = None
    target_config: Optional[dict] = None
    notification_channels: Optional[List[str]] = None
    notification_config: Optional[dict] = None
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    usage_limit: Optional[int] = None


# ==========================================
# Endpoints
# ==========================================

@router.get("")
async def list_campaigns(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    admin: dict = Depends(require_admin),
):
    """List all campaigns."""
    query = supabase.table("campaigns").select("*").order("created_at", desc=True)

    if status:
        query = query.eq("status", status)

    offset = (page - 1) * limit
    result = query.range(offset, offset + limit - 1).execute()

    return {"campaigns": result.data or [], "page": page}


@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    admin: dict = Depends(require_admin),
):
    """Get campaign details."""
    result = supabase.table("campaigns").select("*").eq("id", campaign_id).execute()

    if not result.data:
        raise HTTPException(404, "Campaign not found")

    return result.data[0]


@router.post("")
async def create_campaign(
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

    result = supabase.table("campaigns").insert(campaign_data).execute()

    if not result.data:
        raise HTTPException(500, "Failed to create campaign")

    return result.data[0]


@router.put("/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    req: CampaignUpdateRequest,
    admin: dict = Depends(require_admin),
):
    """Update a campaign."""
    update_data = {k: v for k, v in req.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(400, "No fields to update")

    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = supabase.table("campaigns").update(update_data).eq("id", campaign_id).execute()

    if not result.data:
        raise HTTPException(404, "Campaign not found")

    return result.data[0]


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    admin: dict = Depends(require_admin),
):
    """Delete a campaign (soft delete)."""
    result = supabase.table("campaigns").update({
        "status": "deleted",
        "is_active": False,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", campaign_id).execute()

    if not result.data:
        raise HTTPException(404, "Campaign not found")

    return {"status": "deleted", "campaign_id": campaign_id}


@router.post("/{campaign_id}/activate")
async def activate_campaign(
    campaign_id: str,
    admin: dict = Depends(require_admin),
):
    """Activate a campaign."""
    result = supabase.table("campaigns").update({
        "status": "active",
        "is_active": True,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", campaign_id).execute()

    if not result.data:
        raise HTTPException(404, "Campaign not found")

    return {"status": "activated", "campaign_id": campaign_id}


@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: str,
    admin: dict = Depends(require_admin),
):
    """Pause a campaign."""
    result = supabase.table("campaigns").update({
        "status": "paused",
        "is_active": False,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", campaign_id).execute()

    if not result.data:
        raise HTTPException(404, "Campaign not found")

    return {"status": "paused", "campaign_id": campaign_id}


@router.get("/{campaign_id}/stats")
async def get_campaign_stats(
    campaign_id: str,
    admin: dict = Depends(require_admin),
):
    """Get campaign statistics."""
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
