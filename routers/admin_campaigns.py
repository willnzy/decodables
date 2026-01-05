"""
Admin Campaigns Router - Campaign management for admins

@module routers.admin_campaigns
@version 3.24

Endpoints:
- GET /api/admin/campaigns - List campaigns
- GET /api/admin/campaigns/{id} - Get campaign
- POST /api/admin/campaigns - Create campaign
- PUT /api/admin/campaigns/{id} - Update campaign
- DELETE /api/admin/campaigns/{id} - Delete campaign
- POST /api/admin/campaigns/{id}/activate - Activate campaign
- POST /api/admin/campaigns/{id}/pause - Pause campaign
- GET /api/admin/campaigns/{id}/stats - Get campaign stats
"""

import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from dependencies import require_admin
from services.db_service import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/campaigns", tags=["admin-campaigns"])


# ==========================================
# Request Models
# ==========================================

class CampaignCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    type: str  # credits_gift, credits_discount, credits_bonus
    config: dict
    target_type: str  # all, tier, user_list
    target_config: Optional[dict] = None
    notification_channels: List[str] = []
    notification_config: Optional[dict] = None
    start_at: str
    end_at: Optional[str] = None
    timezone: str = "UTC"
    usage_limit: Optional[int] = None
    usage_per_user: Optional[int] = None


class CampaignUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[dict] = None
    target_type: Optional[str] = None
    target_config: Optional[dict] = None
    notification_channels: Optional[List[str]] = None
    notification_config: Optional[dict] = None
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    timezone: Optional[str] = None
    usage_limit: Optional[int] = None
    usage_per_user: Optional[int] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None


# ==========================================
# Campaign Routes
# ==========================================

@router.get("")
def list_campaigns(
    status: Optional[str] = None,
    type: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    admin: dict = Depends(require_admin)
):
    """List all campaigns with filtering."""
    query = supabase.table('campaigns').select('*', count='exact')
    
    if status:
        query = query.eq('status', status)
    if type:
        query = query.eq('type', type)
    
    offset = (page - 1) * limit
    result = query.order('created_at', desc=True).range(offset, offset + limit - 1).execute()
    
    return {
        "items": result.data or [],
        "total": result.count or 0,
        "page": page,
        "limit": limit
    }


@router.get("/{campaign_id}")
def get_campaign(campaign_id: str, admin: dict = Depends(require_admin)):
    """Get campaign details."""
    result = supabase.table('campaigns').select('*').eq('id', campaign_id).execute()
    if not result.data:
        raise HTTPException(404, "Campaign not found")
    return result.data[0]


@router.post("")
def create_campaign(req: CampaignCreateRequest, admin: dict = Depends(require_admin)):
    """Create a new campaign."""
    now = datetime.utcnow()
    start_at = datetime.fromisoformat(req.start_at.replace('Z', '+00:00'))
    status = 'scheduled' if start_at.replace(tzinfo=None) > now else 'active'
    
    data = {
        "name": req.name,
        "description": req.description,
        "type": req.type,
        "config": req.config,
        "target_type": req.target_type,
        "target_config": req.target_config or {},
        "notification_channels": req.notification_channels,
        "notification_config": req.notification_config or {},
        "start_at": req.start_at,
        "end_at": req.end_at,
        "timezone": req.timezone,
        "usage_limit": req.usage_limit,
        "usage_per_user": req.usage_per_user,
        "status": status,
        "created_by": admin['id'],
    }
    
    result = supabase.table('campaigns').insert(data).execute()
    if not result.data:
        raise HTTPException(500, "Failed to create campaign")
    
    return {"status": "created", "campaign": result.data[0]}


@router.put("/{campaign_id}")
def update_campaign(
    campaign_id: str,
    req: CampaignUpdateRequest,
    admin: dict = Depends(require_admin)
):
    """Update campaign."""
    update_data = {k: v for k, v in req.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(400, "No update data provided")
    
    result = supabase.table('campaigns').update(update_data).eq('id', campaign_id).execute()
    if not result.data:
        raise HTTPException(404, "Campaign not found")
    
    return {"status": "updated", "campaign": result.data[0]}


@router.delete("/{campaign_id}")
def delete_campaign(campaign_id: str, admin: dict = Depends(require_admin)):
    """Soft delete campaign."""
    result = supabase.table('campaigns').update({"is_deleted": True}).eq('id', campaign_id).execute()
    if not result.data:
        raise HTTPException(404, "Campaign not found")
    return {"status": "deleted", "campaign_id": campaign_id}


@router.post("/{campaign_id}/activate")
def activate_campaign(campaign_id: str, admin: dict = Depends(require_admin)):
    """Activate a campaign."""
    result = supabase.table('campaigns').update({"status": "active"}).eq('id', campaign_id).execute()
    if not result.data:
        raise HTTPException(404, "Campaign not found")
    return {"status": "activated", "campaign_id": campaign_id}


@router.post("/{campaign_id}/pause")
def pause_campaign(campaign_id: str, admin: dict = Depends(require_admin)):
    """Pause a campaign."""
    result = supabase.table('campaigns').update({"status": "paused"}).eq('id', campaign_id).execute()
    if not result.data:
        raise HTTPException(404, "Campaign not found")
    return {"status": "paused", "campaign_id": campaign_id}


@router.get("/{campaign_id}/stats")
def get_campaign_stats(campaign_id: str, admin: dict = Depends(require_admin)):
    """Get campaign usage statistics."""
    campaign = supabase.table('campaigns').select('*').eq('id', campaign_id).execute()
    if not campaign.data:
        raise HTTPException(404, "Campaign not found")
    
    claims = supabase.table('campaign_claims').select('*', count='exact').eq('campaign_id', campaign_id).execute()
    
    return {
        "campaign_id": campaign_id,
        "total_claims": claims.count or 0,
        "usage_limit": campaign.data[0].get("usage_limit"),
        "claims": claims.data[:100] if claims.data else []
    }
