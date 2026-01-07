"""
Marketplace API - Marketplace listings and purchases.

@module api.user.marketplace
@version 1.0.0

Endpoints:
- GET /api/v2/user/marketplace/listings - List marketplace items
- GET /api/v2/user/marketplace/listings/{id} - Get single listing
- POST /api/v2/user/marketplace/listings - Publish to marketplace
- PUT /api/v2/user/marketplace/listings/{id} - Update listing
- DELETE /api/v2/user/marketplace/listings/{id} - Unpublish listing
- POST /api/v2/user/marketplace/purchase - Purchase an item
- GET /api/v2/user/marketplace/my-listings - Get user's listings
- GET /api/v2/user/marketplace/seller/stats - Get seller statistics
"""

import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from dependencies import get_current_user, require_member
from container import get_container
from services.rate_limiter import limiter

from application.commands.marketplace import (
    CreateListingCommand,
    PurchaseListingCommand,
)
from application.queries.marketplace import (
    GetListingQuery,
    SearchListingsQuery,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/marketplace", tags=["user-marketplace-v2"])


# ==========================================
# Request/Response Models
# ==========================================

class ListingCreateRequest(BaseModel):
    """Request to create a listing."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    resource_url: Optional[str] = None
    resource_type: str = Field(..., pattern="^(asset|project)$")
    resource_id: Optional[str] = None
    price_credits: int = Field(0, ge=0, le=500)
    allowed_tiers: Optional[List[str]] = None
    version: Optional[str] = "1.0"
    changelog: Optional[str] = None


class ListingUpdateRequest(BaseModel):
    """Request to update a listing."""
    title: Optional[str] = None
    description: Optional[str] = None
    price_credits: Optional[int] = Field(None, ge=0, le=500)
    allowed_tiers: Optional[List[str]] = None


class PurchaseRequest(BaseModel):
    """Request to purchase a listing."""
    listing_id: str
    idempotency_key: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    referral_context: Optional[str] = None


class ListingResponse(BaseModel):
    """Single listing response."""
    id: str
    seller_id: str
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    resource_type: str
    price_credits: int = 0
    allowed_tiers: List[str] = ["free"]
    moderation_status: str = "draft"
    usage_count: int = 0
    created_at: Optional[str] = None

    class Config:
        extra = "allow"


class ListingsResponse(BaseModel):
    """Listings list response."""
    items: List[Dict[str, Any]]
    total: int
    page: int


class PurchaseResponse(BaseModel):
    """Purchase response."""
    success: bool
    listing_id: str
    project_id: Optional[str] = None
    already_owned: bool = False
    credits_deducted: int = 0


class SellerStatsResponse(BaseModel):
    """Seller statistics response."""
    total_earned_credits: int = 0
    listings_count: int = 0
    total_sales: int = 0
    total_usage: int = 0


# ==========================================
# Endpoints
# ==========================================

@router.get("/listings")
@limiter.limit("60/minute")
async def list_listings(
    request: Request,
    featured: bool = False,
    resource_type: Optional[str] = None,
    sort: str = Query("latest", pattern="^(latest|popular|price_asc|price_desc)$"),
    tier: Optional[str] = None,
    price: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
) -> ListingsResponse:
    """
    Get marketplace listings with filters.

    Args:
        featured: Only show featured listings
        resource_type: Filter by 'asset' or 'project'
        sort: Sort order (latest, popular, price_asc, price_desc)
        tier: Filter by tier requirement
        price: Price filter (e.g., 'free', '1-100')
        page: Page number
        limit: Items per page

    Returns:
        ListingsResponse with paginated listings
    """
    container = get_container()
    handler = container.search_listings_handler

    query = SearchListingsQuery(
        user_id=user["id"],
        user_tier=user.get("tier", "free"),
        resource_type=resource_type,
        featured=featured,
        sort=sort,
        page=page,
        limit=limit,
    )

    result = await handler.handle(query)

    if not result.success:
        logger.error(f"Failed to get listings: {result.error}")
        raise HTTPException(500, "Failed to get listings")

    return ListingsResponse(
        items=result.listings_list,
        total=result.total_count,
        page=page,
    )


@router.get("/listings/{listing_id}")
async def get_listing(
    listing_id: str,
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get single listing details.

    Returns:
        Listing details
    """
    container = get_container()
    handler = container.get_listing_handler

    query = GetListingQuery(
        listing_id=listing_id,
        user_id=user["id"],
    )

    result = await handler.handle(query)

    if not result.success:
        if "not found" in (result.error or "").lower():
            raise HTTPException(404, "Listing not found")
        raise HTTPException(400, result.error or "Failed to get listing")

    return result.listing_dict


@router.post("/listings")
@limiter.limit("10/minute")
async def create_listing(
    request: Request,
    req: ListingCreateRequest,
    user: dict = Depends(require_member),
) -> Dict[str, Any]:
    """
    Publish to marketplace (submit for review).

    Requires membership:
    - Starter: only free assets (price_credits=0, resource_type='asset')
    - Pro: any price 0-500, assets or projects

    Returns:
        Created listing with moderation_status='pending'
    """
    container = get_container()
    handler = container.create_listing_handler

    user_tier = (user.get("tier") or "free").lower()

    # Validate publish permission based on tier
    if user_tier == "starter":
        if req.resource_type != "asset":
            raise HTTPException(403, "Starter users can only publish assets")
        if req.price_credits > 0:
            raise HTTPException(403, "Starter users can only publish free assets")

    command = CreateListingCommand(
        seller_id=user["id"],
        title=req.title,
        description=req.description,
        thumbnail_url=req.thumbnail_url,
        resource_url=req.resource_url,
        resource_type=req.resource_type,
        resource_id=req.resource_id,
        price_credits=req.price_credits,
        allowed_tiers=req.allowed_tiers or ["free"],
        version=req.version,
        changelog=req.changelog,
    )

    result = await handler.handle(command)

    if not result.success:
        raise HTTPException(400, result.error or "Failed to create listing")

    return {
        "listing_id": result.listing_id,
        "moderation_status": "pending",
        "message": "Submitted for review",
    }


@router.put("/listings/{listing_id}")
async def update_listing(
    listing_id: str,
    req: ListingUpdateRequest,
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Update a listing (seller only).

    State machine:
    - draft: can edit all fields
    - pending: cannot edit
    - approved: critical changes go back to pending
    - rejected: can edit and resubmit

    Returns:
        Update status
    """
    container = get_container()
    marketplace_service = container.marketplace_service

    try:
        result = await marketplace_service.update_listing(
            listing_id=listing_id,
            seller_id=user["id"],
            title=req.title,
            description=req.description,
            price_credits=req.price_credits,
            allowed_tiers=req.allowed_tiers,
        )

        if not result.success:
            if "not found" in (result.error or "").lower():
                raise HTTPException(404, "Listing not found")
            if "pending" in (result.error or "").lower():
                raise HTTPException(400, "Cannot edit pending listing")
            raise HTTPException(400, result.error)

        return {
            "status": "updated",
            "listing_id": listing_id,
            "requires_resubmit": result.requires_resubmit,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update listing {listing_id}: {e}")
        raise HTTPException(400, str(e))


@router.delete("/listings/{listing_id}")
async def unpublish_listing(
    listing_id: str,
    user: dict = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Unpublish a listing (set is_public=false).

    Only listing owner can unpublish.

    Returns:
        Status
    """
    container = get_container()
    marketplace_service = container.marketplace_service

    try:
        result = await marketplace_service.unpublish_listing(
            listing_id=listing_id,
            seller_id=user["id"],
        )

        if not result.success:
            if "not found" in (result.error or "").lower():
                raise HTTPException(404, "Listing not found")
            raise HTTPException(400, result.error)

        return {"status": "unpublished"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unpublish listing {listing_id}: {e}")
        raise HTTPException(400, str(e))


@router.post("/purchase")
@limiter.limit("10/minute")
async def purchase_listing(
    request: Request,
    req: PurchaseRequest,
    user: dict = Depends(get_current_user),
) -> PurchaseResponse:
    """
    Purchase a marketplace item.

    Cross-domain operation:
    - Validates listing access
    - Deducts credits (monthly first, then permanent)
    - Creates project copy for buyer
    - Records seller earnings (90%)

    Returns:
        Purchase result
    """
    container = get_container()
    handler = container.purchase_listing_handler

    command = PurchaseListingCommand(
        listing_id=req.listing_id,
        buyer_id=user["id"],
        buyer_tier=user.get("tier", "free"),
        idempotency_key=req.idempotency_key,
    )

    result = await handler.handle(command)

    if not result.success:
        error = result.error or "Purchase failed"

        if "insufficient" in error.lower():
            raise HTTPException(402, error)
        if "not found" in error.lower():
            raise HTTPException(404, "Listing not found")
        if "access" in error.lower() or "tier" in error.lower():
            raise HTTPException(403, error)

        raise HTTPException(400, error)

    return PurchaseResponse(
        success=True,
        listing_id=req.listing_id,
        project_id=result.project_id,
        already_owned=result.already_owned,
        credits_deducted=result.credits_deducted,
    )


@router.get("/my-listings")
async def get_my_listings(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
) -> ListingsResponse:
    """
    Get user's own listings (all moderation states).

    Returns:
        Own listings with moderation info
    """
    container = get_container()
    marketplace_service = container.marketplace_service

    try:
        listings = await marketplace_service.get_seller_listings(
            seller_id=user["id"],
            page=page,
            limit=limit,
        )

        return ListingsResponse(
            items=[l.to_dict() for l in listings],
            total=len(listings),
            page=page,
        )

    except Exception as e:
        logger.error(f"Failed to get my listings: {e}")
        raise HTTPException(500, "Failed to get listings")


@router.get("/seller/stats", response_model=SellerStatsResponse)
async def get_seller_stats(
    user: dict = Depends(get_current_user),
) -> SellerStatsResponse:
    """
    Get seller statistics.

    Returns:
        total_earned_credits, listings_count, total_sales, total_usage
    """
    container = get_container()
    marketplace_service = container.marketplace_service

    try:
        stats = await marketplace_service.get_seller_stats(user["id"])

        return SellerStatsResponse(
            total_earned_credits=stats.get("total_earned_credits", 0),
            listings_count=stats.get("listings_count", 0),
            total_sales=stats.get("total_sales", 0),
            total_usage=stats.get("total_usage", 0),
        )

    except Exception as e:
        logger.error(f"Failed to get seller stats: {e}")
        raise HTTPException(500, "Failed to get stats")


# ==========================================
# Leaderboard Endpoint
# ==========================================

class LeaderboardItem(BaseModel):
    """Leaderboard item."""
    listing_id: str
    title: str
    seller_id: str
    usage_count: int
    resource_type: str


class LeaderboardResponse(BaseModel):
    """Leaderboard response."""
    items: List[Dict[str, Any]]
    period: str
    type: str


@router.get("/leaderboard")
async def get_leaderboard(
    period: str = Query("monthly", pattern="^(monthly|all_time)$"),
    type: str = Query("all", pattern="^(all|project|asset)$"),
    user: dict = Depends(get_current_user),
) -> LeaderboardResponse:
    """
    Get marketplace leaderboard.

    Only includes approved + public + not deleted listings.

    Args:
        period: 'monthly' | 'all_time'
        type: 'all' | 'project' | 'asset'

    Returns:
        Top listings by usage_count
    """
    container = get_container()
    marketplace_service = container.marketplace_service

    try:
        items = await marketplace_service.get_leaderboard(period, type)

        return LeaderboardResponse(
            items=items,
            period=period,
            type=type,
        )

    except Exception as e:
        logger.error(f"Failed to get leaderboard: {e}")
        raise HTTPException(500, "Failed to get leaderboard")


# ==========================================
# Report Endpoints
# ==========================================

class ReportRequest(BaseModel):
    """Report request."""
    listing_id: str
    reason: str = Field(..., min_length=1, max_length=1000)


class ReportResponse(BaseModel):
    """Report response."""
    success: bool
    report_id: Optional[str] = None
    message: str


class ReportItem(BaseModel):
    """Report item."""
    id: str
    listing_id: str
    reason: str
    status: str
    created_at: Optional[str] = None


class MyReportsResponse(BaseModel):
    """My reports response."""
    items: List[Dict[str, Any]]
    total: int


@router.post("/report")
@limiter.limit("10/minute")
async def submit_report(
    request: Request,
    req: ReportRequest,
    user: dict = Depends(get_current_user),
) -> ReportResponse:
    """
    Submit a content report for a marketplace listing.

    Users can report listings for copyright violations, inappropriate content, etc.

    Args:
        req: Report request with listing_id and reason

    Returns:
        Report confirmation with report_id

    Raises:
        HTTPException: 400 if already reported, 500 if failed
    """
    from services.db_service import create_report, log_activity

    try:
        report = create_report(user["id"], req.listing_id, req.reason)
        if report:
            log_activity(user["id"], "submit_report", {"listing_id": req.listing_id})
            return ReportResponse(
                success=True,
                report_id=report["id"],
                message="Report submitted successfully",
            )
        raise HTTPException(500, "Failed to submit report")

    except Exception as e:
        error_msg = str(e)
        if "already reported" in error_msg.lower():
            raise HTTPException(400, error_msg)
        raise HTTPException(500, error_msg)


@router.get("/my-reports")
async def get_my_reports(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
) -> MyReportsResponse:
    """
    Get reports submitted by the current user.

    Args:
        page: Page number (default: 1)
        limit: Items per page (default: 20)

    Returns:
        List of user's reports
    """
    from services.db_service import get_user_reports

    reports = get_user_reports(user["id"], page, limit)
    return MyReportsResponse(
        items=reports,
        total=len(reports),
    )
