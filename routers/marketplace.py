"""
Marketplace Router
Handles marketplace-related API endpoints

@module routers/marketplace
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Request
from dependencies import get_current_user, require_member
from db_service import (
    get_marketplace_listings, get_marketplace_item, 
    create_listing, submit_listing_for_review, unpublish_listing as db_unpublish,
    get_leaderboard, supabase
)
from schemas import (
    ListingCreate, ListingUpdate, PurchaseRequest,
    PurchaseResult, SellerStats, PaginatedResponse
)
from exceptions import (
    ListingNotFoundException, ForbiddenException,
    InvalidTiersException, CannotEditPendingException,
    InsufficientCreditsException
)
from services import get_access_control, get_marketplace_service
from timezone_utils import get_request_timezone

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])


# Backwards compatible request models (for unpublish)
from pydantic import BaseModel

class UnpublishRequest(BaseModel):
    listing_id: str


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
        ListingNotFoundException: If not found or not accessible
    
    Returns:
        Listing details
    """
    item = get_marketplace_item(listing_id, user["id"])
    if not item:
        raise ListingNotFoundException(listing_id)
    return item


@router.post("/publish")
def publish_item(request: Request, req: ListingCreate, user: dict = Depends(require_member)):
    """
    Publish to marketplace (submit for review).
    
    Requires membership. Validates:
    - Starter: only free assets (price_credits=0, resource_type='asset')
    - Pro: any price 0-500, assets or projects
    
    Returns:
        Created listing with moderation_status='pending'
    """
    access_control = get_access_control()
    
    # Check publish permission
    allowed, reason = access_control.publish_permission(user, req.resource_type, req.price_credits)
    if not allowed:
        raise ForbiddenException(reason)
    
    # Validate allowed_tiers (already validated by schema, but double-check)
    if req.allowed_tiers and not access_control.validate_allowed_tiers(req.allowed_tiers):
        raise InvalidTiersException()
    
    # v3.9: Get timezone from request for snapshot
    tz = get_request_timezone(request, user_id=user.get("id"))
    
    # Create listing
    listing = create_listing(
        seller_id=user["id"],
        title=req.title,
        description=req.description,
        thumbnail_url=req.thumbnail_url,
        resource_url=req.resource_url,
        resource_type=req.resource_type,
        price_credits=req.price_credits,
        allowed_tiers=req.allowed_tiers or ["free"],
        resource_id=req.resource_id,  # Pass the actual resource ID
        version=req.version or "1.0",
        changelog=req.changelog or "",
        timezone=tz
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
        ListingNotFoundException: If not found or not authorized
    
    Returns:
        Status
    """
    result = db_unpublish(req.listing_id, user["id"])
    if not result:
        raise ListingNotFoundException(req.listing_id)
    return {"status": "unpublished"}


@router.post("/purchase")
def purchase_item(request: Request, req: PurchaseRequest, user: dict = Depends(get_current_user)):
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
    # v3.9: Get timezone from request for snapshot
    tz = get_request_timezone(request, user_id=user.get("id"))
    
    marketplace_service = get_marketplace_service()
    result = marketplace_service.execute_purchase(req.listing_id, user["id"], timezone=tz)
    
    if not result.get("success"):
        error = result.get("error", "Purchase failed")
        status = result.get("status", 400)
        
        if status == 402:
            raise InsufficientCreditsException()
        elif status == 403:
            raise ForbiddenException(error)
        elif status == 404:
            raise ListingNotFoundException(req.listing_id)
        else:
            from fastapi import HTTPException
            raise HTTPException(status_code=status, detail=error)
    
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
    req: ListingUpdate, 
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
    access_control = get_access_control()
    
    # Get listing and verify ownership
    listing = get_marketplace_item(listing_id, user["id"])
    if not listing:
        raise ListingNotFoundException(listing_id)
    
    if listing.get("seller_id") != user["id"]:
        raise ForbiddenException("Not authorized to edit this listing")
    
    status = listing.get("moderation_status", "draft")
    
    # Pending listings cannot be edited
    if status == "pending":
        raise CannotEditPendingException()
    
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
            allowed, reason = access_control.publish_permission(user, listing.get("resource_type"), req.price_credits)
            if not allowed:
                raise ForbiddenException(reason)
            updates["price_credits"] = req.price_credits
            if status == "approved":
                requires_resubmit = True
    
    if req.allowed_tiers is not None:
        if not access_control.validate_allowed_tiers(req.allowed_tiers):
            raise InvalidTiersException()
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


@router.get("/seller/stats", response_model=SellerStats)
def get_seller_stats(user: dict = Depends(get_current_user)):
    """
    Get seller statistics.
    
    Returns:
        total_earned_credits, listings_count, total_sales, total_usage
    """
    marketplace_service = get_marketplace_service()
    return marketplace_service.get_seller_stats(user["id"])


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
        type: 'all' | 'project' | 'asset'
    
    Returns:
        Top listings by usage_count
    """
    marketplace_service = get_marketplace_service()
    return marketplace_service.get_leaderboard(period, type)

