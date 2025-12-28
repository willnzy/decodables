"""
Admin Router
Handles admin-related API endpoints

@module routers/admin
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from dependencies import require_admin
from db_service import (
    admin_search_users, admin_get_user_audit, admin_adjust_credits,
    admin_update_tier, admin_create_discount, admin_broadcast,
    admin_restore_project, admin_get_projects_feed,
    admin_get_moderation_list, get_marketplace_item,
    admin_approve_listing, admin_reject_listing, 
    admin_delete_listing, admin_unpublish_listing
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# Request Models
class CreditAdjustRequest(BaseModel):
    user_id: str
    amount: int
    bucket: str = "permanent"  # 'monthly' | 'permanent'
    reason: Optional[str] = None


class TierUpdateRequest(BaseModel):
    user_id: str
    tier: str  # 'free' | 'starter' | 'pro'


class DiscountRequest(BaseModel):
    user_id: str
    discount_percent: int
    valid_days: int
    target_plan: Optional[str] = None


class BroadcastRequest(BaseModel):
    title: str
    content: str
    target_group: str = "all"  # 'all' | 'free' | 'starter' | 'pro'


class RejectRequest(BaseModel):
    reason: str


# User Management Routes
@router.get("/users")
def search_users(query: str, admin: dict = Depends(require_admin)):
    """
    Search users by email or username.
    
    Returns:
        Matching users
    """
    return admin_search_users(query)


@router.get("/user/{user_id}")
def get_user_audit(user_id: str, admin: dict = Depends(require_admin)):
    """
    Get full user audit data.
    
    Returns:
        User profile, credits, transactions, projects, etc.
    """
    return admin_get_user_audit(user_id)


@router.post("/credits/adjust")
def adjust_credits(req: CreditAdjustRequest, admin: dict = Depends(require_admin)):
    """
    Adjust user credits.
    
    Args:
        user_id: Target user
        amount: Amount to add (negative to deduct)
        bucket: 'monthly' or 'permanent'
        reason: Reason for adjustment
    
    Returns:
        Updated credit balances
    """
    return admin_adjust_credits(
        req.user_id, 
        req.amount, 
        req.bucket, 
        req.reason,
        admin["id"]
    )


@router.post("/tier/update")
def update_tier(req: TierUpdateRequest, admin: dict = Depends(require_admin)):
    """
    Update user tier.
    
    Returns:
        Updated profile
    """
    return admin_update_tier(req.user_id, req.tier)


@router.post("/discount")
def create_discount(req: DiscountRequest, admin: dict = Depends(require_admin)):
    """
    Create discount for user.
    
    Returns:
        Created discount
    """
    return admin_create_discount(
        req.user_id,
        req.discount_percent,
        req.valid_days,
        req.target_plan
    )


@router.post("/broadcast")
def broadcast(req: BroadcastRequest, admin: dict = Depends(require_admin)):
    """
    Broadcast notification to users.
    
    Returns:
        Created notification
    """
    return admin_broadcast(req.title, req.content, req.target_group)


# Project Management Routes
@router.post("/projects/{project_id}/restore")
def restore_project(project_id: str, admin: dict = Depends(require_admin)):
    """
    Restore a deleted project.
    
    Raises:
        HTTPException: 404 if not found
    
    Returns:
        Restored project
    """
    result = admin_restore_project(project_id)
    if not result:
        raise HTTPException(404, "Project not found")
    return result


@router.get("/projects/feed")
def get_projects_feed(page: int = 1, limit: int = 50, admin: dict = Depends(require_admin)):
    """
    Get all projects feed (time desc).
    
    Returns:
        Projects with user info
    """
    items = admin_get_projects_feed(page, limit)
    return {"items": items, "total": len(items), "page": page}


# Marketplace Moderation Routes
@router.get("/marketplace/moderation/list")
def get_moderation_list(
    status: Optional[str] = None,
    type: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    admin: dict = Depends(require_admin)
):
    """
    Get moderation queue.
    
    Args:
        status: Filter by moderation_status (pending/approved/rejected)
        type: Filter by resource_type (template/asset)
    
    Returns:
        Listings with seller info
    """
    items = admin_get_moderation_list(status, type, page, limit)
    return {"items": items, "total": len(items), "page": page}


@router.get("/marketplace/moderation/{listing_id}")
def get_moderation_detail(listing_id: str, admin: dict = Depends(require_admin)):
    """
    Get listing detail for moderation.
    
    Returns:
        Full listing with seller info
    """
    item = get_marketplace_item(listing_id, admin["id"])
    if not item:
        raise HTTPException(404, "Listing not found")
    return item


@router.post("/marketplace/moderation/{listing_id}/approve")
def approve_listing(listing_id: str, admin: dict = Depends(require_admin)):
    """
    Approve a listing.
    
    Returns:
        Updated listing
    """
    result = admin_approve_listing(listing_id, admin["id"])
    if not result:
        raise HTTPException(404, "Listing not found")
    return {"status": "approved", "listing_id": listing_id}


@router.post("/marketplace/moderation/{listing_id}/reject")
def reject_listing(listing_id: str, req: RejectRequest, admin: dict = Depends(require_admin)):
    """
    Reject a listing with reason.
    
    Returns:
        Updated listing
    """
    result = admin_reject_listing(listing_id, admin["id"], req.reason)
    if not result:
        raise HTTPException(404, "Listing not found")
    return {"status": "rejected", "listing_id": listing_id, "reason": req.reason}


@router.post("/marketplace/moderation/{listing_id}/delete")
def delete_listing(listing_id: str, admin: dict = Depends(require_admin)):
    """
    Soft delete a listing.
    
    Returns:
        Status
    """
    result = admin_delete_listing(listing_id, admin["id"])
    if not result:
        raise HTTPException(404, "Listing not found")
    return {"status": "deleted", "listing_id": listing_id}


@router.post("/marketplace/moderation/{listing_id}/unpublish")
def unpublish_listing(listing_id: str, admin: dict = Depends(require_admin)):
    """
    Force unpublish a listing.
    
    Returns:
        Status
    """
    result = admin_unpublish_listing(listing_id, admin["id"])
    if not result:
        raise HTTPException(404, "Listing not found")
    return {"status": "unpublished", "listing_id": listing_id}

