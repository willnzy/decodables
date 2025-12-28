"""
Marketplace Router
Handles marketplace-related API endpoints

@module routers/marketplace
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator
from dependencies import get_current_user, require_member
from db_service import (
    get_marketplace_listings, get_marketplace_item, 
    create_listing, submit_listing_for_review, unpublish_listing as db_unpublish,
    execute_purchase, get_seller_stats as db_seller_stats,
    get_leaderboard, publish_permission, validate_allowed_tiers, is_member
)
from config import MAX_LISTING_PRICE

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])


# Request Models
class PublishRequest(BaseModel):
    title: str
    description: Optional[str] = ""
    thumbnail_url: str
    resource_url: str
    resource_type: str  # 'template' | 'asset'
    price_credits: int = 0
    allowed_tiers: List[str] = None
    
    @field_validator('price_credits')
    @classmethod
    def validate_price(cls, v):
        if v < 0 or v > MAX_LISTING_PRICE:
            raise ValueError(f'price_credits must be between 0 and {MAX_LISTING_PRICE}')
        return v
    
    @field_validator('resource_type')
    @classmethod
    def validate_type(cls, v):
        if v not in ['template', 'asset']:
            raise ValueError('resource_type must be template or asset')
        return v


class PurchaseRequest(BaseModel):
    listing_id: str


class UnpublishRequest(BaseModel):
    listing_id: str


class UpdateListingRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price_credits: Optional[int] = None
    allowed_tiers: Optional[List[str]] = None
    
    @field_validator('price_credits')
    @classmethod
    def validate_price(cls, v):
        if v is not None and (v < 0 or v > MAX_LISTING_PRICE):
            raise ValueError(f'price_credits must be between 0 and {MAX_LISTING_PRICE}')
        return v


# Routes
@router.get("/items")
def list_items(
    featured: bool = False,
    resource_type: Optional[str] = None,
    sort: str = "latest",
    tier: Optional[str] = None,
    price: Optional[str] = None,
    mine: bool = False,
    page: int = 1,
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    """
    Get marketplace listings with filters.
    
    Public listings require: moderation_status='approved' AND is_public=true AND is_deleted=false
    mine=true shows user's own listings in all states
    
    Returns:
        Listings with pagination
    """
    items = get_marketplace_listings(
        user_id=user["id"],
        user_tier=user.get("tier", "free"),
        resource_type=resource_type,
        mine=mine,
        page=page,
        limit=limit,
        sort=sort,
        tier_filter=tier,
        price_filter=price
    )
    return {"items": items, "total": len(items), "page": page}


@router.get("/item/{listing_id}")
def get_item(listing_id: str, user: dict = Depends(get_current_user)):
    """
    Get single listing details.
    
    Public access: only approved + public + not deleted
    Seller/Admin: can see all states
    
    Raises:
        HTTPException: 404 if not found or not accessible
    
    Returns:
        Listing details
    """
    item = get_marketplace_item(listing_id, user["id"])
    if not item:
        raise HTTPException(404, "Listing not found")
    return item


@router.post("/publish")
def publish_item(req: PublishRequest, user: dict = Depends(require_member)):
    """
    Publish to marketplace (submit for review).
    
    Requires membership. Validates:
    - Starter: only free assets (price_credits=0, resource_type='asset')
    - Pro: any price 0-500, assets or templates
    
    Returns:
        Created listing with moderation_status='pending'
    """
    # Check publish permission
    allowed, reason = publish_permission(user, req.resource_type, req.price_credits)
    if not allowed:
        raise HTTPException(403, reason)
    
    # Validate allowed_tiers
    if not validate_allowed_tiers(req.allowed_tiers):
        raise HTTPException(400, "Invalid allowed_tiers. Must be ['free'], ['starter','pro'], or ['pro']")
    
    # Create listing
    listing = create_listing(
        seller_id=user["id"],
        title=req.title,
        description=req.description,
        thumbnail_url=req.thumbnail_url,
        resource_url=req.resource_url,
        resource_type=req.resource_type,
        price_credits=req.price_credits,
        allowed_tiers=req.allowed_tiers or ["free"]
    )
    
    # Submit for review (sets moderation_status='pending', is_public=true)
    submit_listing_for_review(listing["id"])
    
    return {
        "listing_id": listing["id"],
        "moderation_status": "pending",
        "message": "Submitted for review"
    }


@router.post("/unpublish")
def unpublish_item(req: UnpublishRequest, user: dict = Depends(get_current_user)):
    """
    Unpublish a listing (set is_public=false).
    Only listing owner can unpublish.
    
    Raises:
        HTTPException: 403 if not owner, 404 if not found
    
    Returns:
        Status
    """
    result = db_unpublish(req.listing_id, user["id"])
    if not result:
        raise HTTPException(404, "Listing not found or not authorized")
    return {"status": "unpublished"}


@router.post("/purchase")
def purchase_item(req: PurchaseRequest, user: dict = Depends(get_current_user)):
    """
    Purchase a marketplace item.
    
    Validates:
    - Listing is approved, public, not deleted
    - User has access based on allowed_tiers
    - User has enough credits
    
    Credits flow: buyer deducts (monthly first), seller receives 90%
    
    Returns:
        Purchase result
    """
    result = execute_purchase(req.listing_id, user["id"])
    if not result.get("success"):
        raise HTTPException(
            status_code=result.get("status", 400),
            detail=result.get("error", "Purchase failed")
        )
    return result


@router.get("/my-listings")
def get_my_listings(page: int = 1, limit: int = 20, user: dict = Depends(get_current_user)):
    """
    Get user's own listings (all moderation states).
    
    Returns:
        Own listings with moderation info
    """
    items = get_marketplace_listings(
        user_id=user["id"],
        user_tier=user.get("tier", "free"),
        mine=True,
        page=page,
        limit=limit
    )
    return {"items": items, "total": len(items), "page": page}


@router.put("/listings/{listing_id}")
def update_listing(
    listing_id: str, 
    req: UpdateListingRequest, 
    user: dict = Depends(get_current_user)
):
    """
    Update a listing (seller only).
    
    PRD v3.2 state machine:
    - draft: can edit all fields and submit -> pending
    - pending: cannot edit (or withdraw to draft)
    - approved: can edit non-critical fields; critical changes go back to pending
    - rejected: can edit and resubmit -> pending
    
    Critical fields: resource_url, allowed_tiers, price_credits
    Non-critical: title, description
    
    Returns:
        Updated listing
    """
    from db_service import supabase
    
    # Get listing and verify ownership
    listing = get_marketplace_item(listing_id, user["id"])
    if not listing:
        raise HTTPException(404, "Listing not found")
    
    if listing.get("seller_id") != user["id"]:
        raise HTTPException(403, "Not authorized to edit this listing")
    
    status = listing.get("moderation_status", "draft")
    
    # Pending listings cannot be edited
    if status == "pending":
        raise HTTPException(400, "Cannot edit listing while pending review")
    
    # Build update dict
    updates = {}
    requires_resubmit = False
    
    if req.title is not None:
        updates["title"] = req.title
    if req.description is not None:
        updates["description"] = req.description
    
    # Critical fields - require re-review if approved
    if req.price_credits is not None:
        # Validate publish permission for new price
        if req.price_credits != listing.get("price_credits"):
            allowed, reason = publish_permission(user, listing.get("resource_type"), req.price_credits)
            if not allowed:
                raise HTTPException(403, reason)
            updates["price_credits"] = req.price_credits
            if status == "approved":
                requires_resubmit = True
    
    if req.allowed_tiers is not None:
        if not validate_allowed_tiers(req.allowed_tiers):
            raise HTTPException(400, "Invalid allowed_tiers")
        updates["allowed_tiers"] = req.allowed_tiers
        if status == "approved":
            requires_resubmit = True
    
    if not updates:
        return {"status": "no_changes", "listing_id": listing_id}
    
    # If critical changes on approved listing, reset to pending
    if requires_resubmit:
        updates["moderation_status"] = "pending"
        updates["moderation_note"] = "Resubmitted after editing critical fields"
    
    # Update
    result = supabase.table("marketplace_listings").update(
        updates
    ).eq("id", listing_id).execute()
    
    return {
        "status": "updated",
        "listing_id": listing_id,
        "requires_resubmit": requires_resubmit
    }


@router.get("/seller/stats")
def get_seller_stats(user: dict = Depends(get_current_user)):
    """
    Get seller statistics.
    
    Returns:
        total_earned_credits, listings_count, total_sales
    """
    return db_seller_stats(user["id"])


@router.get("/leaderboard")
def get_leaderboard_data(
    period: str = "monthly",
    type: str = "all",
    user: dict = Depends(get_current_user)
):
    """
    Get marketplace leaderboard.
    
    Only includes approved + public + not deleted listings.
    
    Args:
        period: 'monthly' | 'all_time'
        type: 'all' | 'template' | 'asset'
    
    Returns:
        Top listings by usage_count
    """
    return get_leaderboard(period, type)

