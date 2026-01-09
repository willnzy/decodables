"""
Admin Campaigns API - Campaign management for admins.

@module api.admin.campaigns
@version 3.30 (DDD Migration)

Changes:
- v3.30: Complete DDD Migration (CAM-CRITICAL-1, CAM-CRITICAL-3)
  - API → Domain Service → Repository
  - Removed direct database access (supabase.table())
  - Constants moved to domains/marketing/campaigns/constants.py
  - Added Audit Log for all mutations
  - All endpoints call Domain Service

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

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

from dependencies import require_admin
from infrastructure.rate_limiter import limiter

# v3.30: Import from Domain layer (DDD Migration)
from domains.marketing.campaigns import (
    list_campaigns,
    get_campaign,
    create_campaign,
    update_campaign,
    delete_campaign,
    activate_campaign,
    pause_campaign,
    get_campaign_stats,
)
from domains.marketing.campaigns.constants import (
    VALID_CAMPAIGN_STATUSES,
    VALID_CAMPAIGN_TYPES,
    VALID_TARGET_TYPES,
    NAME_MIN_LENGTH,
    NAME_MAX_LENGTH,
    DESCRIPTION_MAX_LENGTH,
    USAGE_LIMIT_MIN,
    USAGE_LIMIT_MAX,
    USAGE_PER_USER_MIN,
    USAGE_PER_USER_MAX,
    TIMEZONE_MAX_LENGTH,
    DATETIME_STR_MAX_LENGTH,
    DEFAULT_LIMIT,
    MAX_LIMIT,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/campaigns", tags=["admin-campaigns-v2"])


# ==========================================
# Request Models
# ==========================================

class CampaignCreateRequest(BaseModel):
    """Campaign creation request."""
    name: str = Field(..., min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
    description: Optional[str] = Field(None, max_length=DESCRIPTION_MAX_LENGTH)
    type: str = Field(..., pattern="^(credits_gift|credits_discount|credits_bonus)$")
    config: dict
    target_type: str = Field(..., pattern="^(all|subscription|users|new_users|inactive_users)$")
    target_config: Optional[dict] = None
    notification_channels: List[str] = []
    notification_config: Optional[dict] = None
    start_at: str = Field(..., max_length=DATETIME_STR_MAX_LENGTH)
    end_at: Optional[str] = Field(None, max_length=DATETIME_STR_MAX_LENGTH)
    timezone: str = Field("UTC", max_length=TIMEZONE_MAX_LENGTH)
    usage_limit: Optional[int] = Field(None, ge=USAGE_LIMIT_MIN, le=USAGE_LIMIT_MAX)
    usage_per_user: Optional[int] = Field(None, ge=USAGE_PER_USER_MIN, le=USAGE_PER_USER_MAX)


class CampaignUpdateRequest(BaseModel):
    """Campaign update request."""
    name: Optional[str] = Field(None, min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
    description: Optional[str] = Field(None, max_length=DESCRIPTION_MAX_LENGTH)
    config: Optional[dict] = None
    target_type: Optional[str] = Field(None, max_length=50)
    target_config: Optional[dict] = None
    notification_channels: Optional[List[str]] = None
    notification_config: Optional[dict] = None
    start_at: Optional[str] = Field(None, max_length=DATETIME_STR_MAX_LENGTH)
    end_at: Optional[str] = Field(None, max_length=DATETIME_STR_MAX_LENGTH)
    usage_limit: Optional[int] = Field(None, ge=USAGE_LIMIT_MIN, le=USAGE_LIMIT_MAX)

    @field_validator("target_type")
    @classmethod
    def validate_target_type(cls, v):
        if v is not None and v not in VALID_TARGET_TYPES:
            raise ValueError(f"Invalid target_type. Must be one of: {', '.join(VALID_TARGET_TYPES)}")
        return v


# ==========================================
# Endpoints
# ==========================================

@router.get("")
@limiter.limit("30/minute")
async def list_campaigns_endpoint(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description=f"Page size (1-{MAX_LIMIT})"),
    admin: dict = Depends(require_admin),
):
    """List all campaigns."""
    # v3.30: Status validation
    if status is not None and status not in VALID_CAMPAIGN_STATUSES:
        raise HTTPException(400, f"Invalid status. Must be one of: {', '.join(VALID_CAMPAIGN_STATUSES)}")

    # v3.30: Call Domain Service
    result = await list_campaigns(status=status, offset=offset, limit=limit)
    return result


@router.get("/{campaign_id}")
@limiter.limit("30/minute")
async def get_campaign_endpoint(
    request: Request,
    campaign_id: str,
    admin: dict = Depends(require_admin),
):
    """Get campaign details."""
    # v3.30: Call Domain Service
    campaign = await get_campaign(campaign_id)

    if not campaign:
        raise HTTPException(404, "Campaign not found")

    return campaign


@router.post("")
@limiter.limit("20/minute")
async def create_campaign_endpoint(
    request: Request,
    req: CampaignCreateRequest,
    admin: dict = Depends(require_admin),
):
    """Create a new campaign."""
    try:
        # v3.30: Call Domain Service
        campaign = await create_campaign(
            name=req.name,
            description=req.description,
            campaign_type=req.type,
            config=req.config,
            target_type=req.target_type,
            target_config=req.target_config,
            notification_channels=req.notification_channels,
            notification_config=req.notification_config,
            start_at=req.start_at,
            end_at=req.end_at,
            timezone=req.timezone,
            usage_limit=req.usage_limit,
            usage_per_user=req.usage_per_user,
            admin_id=admin["id"],
        )

        if not campaign:
            raise HTTPException(500, "Failed to create campaign")

        return campaign

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create campaign: {e}")
        raise HTTPException(500, "Failed to create campaign")


@router.put("/{campaign_id}")
@limiter.limit("20/minute")
async def update_campaign_endpoint(
    request: Request,
    campaign_id: str,
    req: CampaignUpdateRequest,
    admin: dict = Depends(require_admin),
):
    """Update a campaign."""
    update_data = {k: v for k, v in req.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(400, "No fields to update")

    try:
        # v3.30: Call Domain Service
        campaign = await update_campaign(
            campaign_id=campaign_id,
            update_data=update_data,
            admin_id=admin["id"],
        )

        if not campaign:
            raise HTTPException(404, "Campaign not found")

        return campaign

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update campaign: {e}")
        raise HTTPException(500, "Failed to update campaign")


@router.delete("/{campaign_id}")
@limiter.limit("10/minute")
async def delete_campaign_endpoint(
    request: Request,
    campaign_id: str,
    admin: dict = Depends(require_admin),
):
    """Delete a campaign (soft delete)."""
    try:
        # v3.30: Call Domain Service
        success = await delete_campaign(campaign_id=campaign_id, admin_id=admin["id"])

        if not success:
            raise HTTPException(404, "Campaign not found")

        return {"status": "deleted", "campaign_id": campaign_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete campaign: {e}")
        raise HTTPException(500, "Failed to delete campaign")


@router.post("/{campaign_id}/activate")
@limiter.limit("10/minute")
async def activate_campaign_endpoint(
    request: Request,
    campaign_id: str,
    admin: dict = Depends(require_admin),
):
    """Activate a campaign."""
    try:
        # v3.30: Call Domain Service
        success = await activate_campaign(campaign_id=campaign_id, admin_id=admin["id"])

        if not success:
            raise HTTPException(404, "Campaign not found")

        return {"status": "activated", "campaign_id": campaign_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to activate campaign: {e}")
        raise HTTPException(500, "Failed to activate campaign")


@router.post("/{campaign_id}/pause")
@limiter.limit("10/minute")
async def pause_campaign_endpoint(
    request: Request,
    campaign_id: str,
    admin: dict = Depends(require_admin),
):
    """Pause a campaign."""
    try:
        # v3.30: Call Domain Service
        success = await pause_campaign(campaign_id=campaign_id, admin_id=admin["id"])

        if not success:
            raise HTTPException(404, "Campaign not found")

        return {"status": "paused", "campaign_id": campaign_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause campaign: {e}")
        raise HTTPException(500, "Failed to pause campaign")


@router.get("/{campaign_id}/stats")
@limiter.limit("30/minute")
async def get_campaign_stats_endpoint(
    request: Request,
    campaign_id: str,
    admin: dict = Depends(require_admin),
):
    """Get campaign statistics."""
    try:
        # v3.30: Call Domain Service
        stats = await get_campaign_stats(campaign_id)

        if not stats:
            raise HTTPException(404, "Campaign not found")

        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get campaign stats: {e}")
        raise HTTPException(500, "Failed to get campaign statistics")
