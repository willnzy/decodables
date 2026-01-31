"""
Marketplace API - Marketplace listings and purchases.

@module api.user.marketplace
@version 3.3.0

Changes:
- v3.3.0: DDD pagination compliance
  - GET /listings response changed from {page} to {offset, limit, has_more}
- v3.2.0: API Consolidation Phase 3
  - REMOVED: GET /seller/stats (use /api/v2/user/seller/stats?include=listings)
- v3.1.0 (2026-01-10): P2-047 - SSRF protection for listing creation
  - Added field_validator for thumbnail_url and resource_url in ListingCreateRequest
  - URLs validated against allowed domains whitelist (Supabase, Fal.ai, etc.)
  - Prevents SSRF attacks via localhost/private IPs
- v3.0.0: DDD architecture upgrade - CQRS pattern consistency
  - Created SupportService with report business logic
  - Added 5 new Handlers (GetMyListings, GetSellerStats, GetLeaderboard, CreateReport, GetMyReports)
  - All 11 endpoints now use consistent CQRS pattern (Command/Query → Handler → Service)
  - Eliminated direct Service calls and direct Repository calls
  - Reduced API layer complexity, improved testability

Endpoints:
- GET /api/v2/user/marketplace/listings - List marketplace items
- GET /api/v2/user/marketplace/listings/{id} - Get single listing
- POST /api/v2/user/marketplace/listings - Publish to marketplace
- PUT /api/v2/user/marketplace/listings/{id} - Update listing
- DELETE /api/v2/user/marketplace/listings/{id} - Unpublish listing
- POST /api/v2/user/marketplace/purchase - Purchase an item
- GET /api/v2/user/marketplace/my-listings - Get user's listings

Security Fixes in v2.1.0:
- M-P0-001: Purchase race condition - atomic record_purchase with ON CONFLICT
- M-P0-002: Credit rollback on purchase failure - compensating transactions
- M-P0-003: Listing status re-validation before completing purchase
- M-HIGH-001/002: Accurate pagination total counts
- M-HIGH-003: Exception message sanitization (no internal details exposed)
- M-HIGH-004: Tier validation against database record
- M-MEDIUM-005: Integer arithmetic for revenue calculations
"""

import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field, field_validator

from domains.identity.aggregates.user_profile import UserProfile
from dependencies import get_current_user, require_member
from core.utils.validation import validate_thumbnail_url
from container import get_container
from infrastructure.rate_limiter import limiter

from application.commands.marketplace import (
    CreateListingCommand,
    UpdateListingCommand,
    UnpublishListingCommand,
    PurchaseListingCommand,
    CreateReportCommand,  # v3.0.0
)
from application.queries.marketplace import (
    GetListingQuery,
    SearchListingsQuery,
    GetMyListingsQuery,  # v3.0.0
    GetLeaderboardQuery,  # v3.0.0
    GetMyReportsQuery,  # v3.0.0
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/marketplace", tags=["user-marketplace-v2"])


# ==========================================
# Request/Response Models
# ==========================================

class ListingCreateRequest(BaseModel):
    """
    Request to create a listing.

    Two-level classification:
    - resource_type: "asset" or "project" (top-level)
    - category: specific content type (second-level, optional)
      - For assets: clipart, sticker, background, icon, etc.
      - For projects: template, mini_book, worksheet, flashcard
    - source: where the asset comes from (system, user, ai, community)

    Security:
    - P2-047: thumbnail_url and resource_url are validated for SSRF protection
    - P2-030: All string fields have max_length for DoS protection
    """
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)  # P2-030: DoS protection
    thumbnail_url: Optional[str] = Field(None, max_length=500)  # P2-030 + P2-047: URL length + SSRF
    resource_url: Optional[str] = Field(None, max_length=500)  # P2-030 + P2-047: URL length + SSRF
    resource_type: str = Field(..., pattern="^(asset|project)$")
    category: Optional[str] = Field(None, max_length=50)  # P2-030: DoS protection
    source: str = Field("user", pattern="^(system|user|ai|community)$")
    resource_id: Optional[str] = Field(None, max_length=50)  # P2-030: UUID length
    price_credits: int = Field(0, ge=0, le=500)
    allowed_tiers: Optional[List[str]] = None
    allow_preview: bool = Field(True)  # Whether buyers can preview before purchase
    version: Optional[str] = Field("1.0", max_length=20)  # P2-030: DoS protection
    changelog: Optional[str] = Field(None, max_length=5000)  # P2-030: DoS protection

    @field_validator("thumbnail_url", "resource_url")
    @classmethod
    def validate_urls(cls, v: Optional[str]) -> Optional[str]:
        """Validate URLs for SSRF protection (P2-047)."""
        if v is None:
            return v

        is_valid, error = validate_thumbnail_url(v)
        if not is_valid:
            raise ValueError(f"Invalid URL: {error}")

        return v


class CreateListingResponse(BaseModel):
    """Response after creating a listing (P2-002)."""
    listing_id: str
    moderation_status: str
    message: str


class UpdateListingResponse(BaseModel):
    """Response after updating a listing (P2-002)."""
    status: str
    listing_id: str
    requires_resubmit: bool


class ListingUpdateRequest(BaseModel):
    """Request to update a listing (P2-030: DoS protection)."""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    thumbnail_url: Optional[str] = Field(None, max_length=500)  # P2-047: URL length limit
    resource_url: Optional[str] = Field(None, max_length=500)  # P2-047: URL length limit
    price_credits: Optional[int] = Field(None, ge=0, le=500)
    allowed_tiers: Optional[List[str]] = None
    version: Optional[str] = Field(None, max_length=20)  # Version string
    changelog: Optional[str] = Field(None, max_length=2000)  # What's new

    @field_validator("thumbnail_url", "resource_url")
    @classmethod
    def validate_urls(cls, v: Optional[str]) -> Optional[str]:
        """Validate URLs for SSRF protection (P2-047) — same as ListingCreateRequest."""
        if v is None:
            return v

        is_valid, error = validate_thumbnail_url(v)
        if not is_valid:
            raise ValueError(f"Invalid URL: {error}")

        return v

    @field_validator("allowed_tiers")
    @classmethod
    def validate_tiers(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate allowed_tiers values (only t1/t2/t3 allowed)."""
        if v is None:
            return v
        valid_tiers = {"t1", "t2", "t3"}
        for tier in v:
            if tier not in valid_tiers:
                raise ValueError(f"Invalid tier '{tier}'. Must be one of: t1, t2, t3")
        return v


class PurchaseRequest(BaseModel):
    """Request to purchase a listing (P2-030: DoS protection)."""
    listing_id: str = Field(..., max_length=50)  # UUID
    idempotency_key: Optional[str] = Field(None, max_length=100)
    utm_source: Optional[str] = Field(None, max_length=100)
    utm_medium: Optional[str] = Field(None, max_length=100)
    utm_campaign: Optional[str] = Field(None, max_length=100)
    referral_context: Optional[str] = Field(None, max_length=500)


class ListingResponse(BaseModel):
    """Single listing response."""
    id: str
    seller_id: str
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    resource_type: str
    category: Optional[str] = None  # Specific content type
    source: str = "user"  # system, user, ai, community
    price_credits: int = 0
    allowed_tiers: List[str] = ["t1"]
    moderation_status: str = "draft"
    usage_count: int = 0
    created_at: Optional[str] = None

    class Config:
        extra = "allow"


class ListingsResponse(BaseModel):
    """Listings list response (DDD compliant: offset/limit pagination)."""
    items: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int
    has_more: bool


class PurchaseResponse(BaseModel):
    """Purchase response."""
    success: bool
    listing_id: str
    project_id: Optional[str] = None
    already_owned: bool = False
    credits_deducted: int = 0


# ==========================================
# Endpoints
# ==========================================

@router.get("/listings")
@limiter.limit("60/minute")
async def list_listings(
    request: Request,
    featured: bool = False,
    resource_type: Optional[str] = None,
    sort: str = Query("latest", pattern="^(latest|popular|price_asc|price_desc|best_selling)$"),
    tier: Optional[str] = None,
    price: Optional[str] = None,
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100),
    user: UserProfile = Depends(get_current_user),
) -> ListingsResponse:
    """
    Get marketplace listings with filters.

    Args:
        featured: Only show featured listings (sorted by sales)
        resource_type: Filter by 'asset' or 'project'
        sort: Sort order (latest, popular, price_asc, price_desc, best_selling)
        tier: Filter by tier requirement ('t1', 't2', 't3')
        price: Price filter ('free', 'paid', 'all')
        page: Page number
        limit: Items per page

    Returns:
        ListingsResponse with paginated listings
    """
    container = get_container()
    handler = await container.get_search_listings_handler()

    

    query = SearchListingsQuery(
        query="",
        resource_type=resource_type,  # Top-level: "asset" or "project"
        category=None,  # Second-level category (not used in this API)
        price_filter=price,
        sort_by=sort,
        tier_filter=tier,
        featured=featured,
        limit=limit,
        offset=offset,
    )

    result = await handler.handle(query)

    if not result.success:
        logger.error(f"Failed to get listings: {result.error}")
        raise HTTPException(500, "Failed to get listings")

    # DDD compliant response with offset/limit
    return ListingsResponse(
        items=result.listings_list,
        total=result.total_count,
        offset=offset,
        limit=limit,
        has_more=offset + len(result.listings_list) < result.total_count,
    )


@router.get("/listings/{listing_id}")
async def get_listing(
    listing_id: str = Path(..., pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"),
    user: UserProfile = Depends(get_current_user),
) -> ListingResponse:  # P2-002: Return Pydantic model instead of Dict[str, Any]
    """
    Get single listing details.

    Access control:
    - Seller can always see their own listing
    - Others can only see approved, public, non-deleted listings

    Returns:
        Listing details with is_purchased, seller_username, seller_avatar_url
    """
    container = get_container()
    handler = await container.get_listing_handler()

    query = GetListingQuery(
        listing_id=listing_id,
        user_id=user.user_id,
    )

    result = await handler.handle(query)

    if not result.success:
        if "not found" in (result.error or "").lower():
            raise HTTPException(404, "Listing not found")
        raise HTTPException(400, result.error or "Failed to get listing")

    # P2-002: Return Pydantic model instead of raw dict
    return ListingResponse(**result.listing_dict)


@router.post("/listings")
@limiter.limit("10/minute")
async def create_listing(
    request: Request,
    req: ListingCreateRequest,
    user: dict = Depends(require_member),
) -> CreateListingResponse:
    """
    Publish to marketplace (submit for review).

    Requires membership:
    - t2: only free assets (price_credits=0, resource_type='asset')
    - t3: any price 0-500, assets or projects

    Returns:
        Created listing with moderation_status='pending'
    """
    container = get_container()
    handler = await container.get_create_listing_handler()

    # UserProfile.tier is UserTier enum, get string value
    user_tier = (user.tier.value if user.tier else "t1").lower()

    # Validate publish permission based on tier
    if user_tier == "t2":
        if req.resource_type != "asset":
            raise HTTPException(403, "t2 users can only publish assets")
        if req.price_credits > 0:
            raise HTTPException(403, "t2 users can only publish free assets")

    # Determine category:
    # - If provided, use it
    # - Otherwise, default based on resource_type
    category = req.category
    if not category:
        category = "template" if req.resource_type == "project" else "element"

    # Map price_credits to price_type (must match PriceType enum values)
    price_type = "free" if req.price_credits == 0 else "credits"

    command = CreateListingCommand(
        seller_id=user.user_id,
        resource_type=req.resource_type,  # "asset" or "project"
        category=category,  # Specific content type
        title=req.title,
        description=req.description,
        source=req.source,  # "system", "user", "ai", "community"
        price_type=price_type,
        credit_price=req.price_credits,
        allowed_tiers=req.allowed_tiers,
        tags=None,  # API doesn't provide tags yet
        preview_url=req.thumbnail_url,
        seller_tier=user_tier,
        resource_id=req.resource_id,  # Link back to project/asset
    )

    result = await handler.handle(command)

    if not result.success:
        raise HTTPException(400, result.error or "Failed to create listing")

    # P2-002: Return Pydantic model instead of raw dict
    listing_id = result.listing.listing_id if result.listing else ""

    return CreateListingResponse(
        listing_id=listing_id,
        moderation_status="pending",
        message="Submitted for review",
    )


@router.put("/listings/{listing_id}")
async def update_listing(
    listing_id: str = Path(..., pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"),
    req: ListingUpdateRequest = ...,
    user: UserProfile = Depends(get_current_user),
) -> UpdateListingResponse:  # P2-002: Return Pydantic model instead of Dict[str, Any]
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
    handler = await container.get_update_listing_handler()

    command = UpdateListingCommand(
        listing_id=listing_id,
        user_id=user.user_id,
        title=req.title,
        description=req.description,
        price_credits=req.price_credits,
        allowed_tiers=req.allowed_tiers,
        preview_url=req.thumbnail_url,  # thumbnail_url maps to preview_url
    )

    result = await handler.handle(command)

    if not result.success:
        error_msg = result.error or "Failed to update listing"
        if "not found" in error_msg.lower():
            raise HTTPException(404, "Listing not found")
        if "pending" in error_msg.lower() or "cannot edit" in error_msg.lower():
            raise HTTPException(400, "Cannot edit listing in current status")
        raise HTTPException(400, error_msg)

    # P2-002: Return Pydantic model instead of raw dict
    return UpdateListingResponse(
        status="updated",
        listing_id=listing_id,
        requires_resubmit=result.requires_resubmit,
    )


@router.delete("/listings/{listing_id}")
async def unpublish_listing(
    listing_id: str = Path(..., pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"),
    user: UserProfile = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Unpublish a listing (archive it).

    Only listing owner can unpublish.
    Only published listings can be unpublished.

    Returns:
        Status
    """
    container = get_container()
    handler = await container.get_unpublish_listing_handler()

    command = UnpublishListingCommand(
        listing_id=listing_id,
        user_id=user.user_id,
    )

    result = await handler.handle(command)

    if not result.success:
        error_msg = result.error or "Failed to unpublish listing"
        if "not found" in error_msg.lower():
            raise HTTPException(404, "Listing not found")
        if "access denied" in error_msg.lower():
            raise HTTPException(403, "Not authorized to unpublish this listing")
        if "cannot unpublish" in error_msg.lower():
            raise HTTPException(400, "Listing cannot be unpublished in current status")
        raise HTTPException(400, error_msg)

    return {"status": "unpublished"}


@router.post("/purchase")
@limiter.limit("10/minute")
async def purchase_listing(
    request: Request,
    req: PurchaseRequest,
    user: UserProfile = Depends(get_current_user),
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
    handler = await container.get_purchase_listing_handler()

    # PurchaseListingCommand expects: listing_id, buyer_id, buyer_tier
    # Note: idempotency_key is generated internally by the handler
    command = PurchaseListingCommand(
        listing_id=req.listing_id,
        buyer_id=user.user_id,
        buyer_tier=user.tier or "t1",
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
        credits_deducted=result.credits_spent,
    )


@router.get("/my-listings")
async def get_my_listings(
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, pattern="^(draft|pending|published|rejected|suspended|archived)$"),
    user: UserProfile = Depends(get_current_user),
) -> ListingsResponse:
    """
    Get user's own listings (all moderation states).

    v3.0.0: Now uses GetMyListingsHandler (CQRS pattern).

    Args:
        page: Page number (1-indexed)
        limit: Items per page
        status: Filter by status (draft/pending/published/rejected/suspended/archived)

    Returns:
        Own listings with moderation info
    """
    container = get_container()
    handler = await container.get_my_listings_handler()

    # Convert page to offset
    

    query = GetMyListingsQuery(
        seller_id=user.user_id,
        status=status,
        limit=limit,
        offset=offset,
    )

    result = await handler.handle(query)

    if not result.success:
        logger.error(f"Failed to get my listings: {result.error}")
        raise HTTPException(500, "Failed to get listings")

    # DDD compliant response with offset/limit
    return ListingsResponse(
        items=result.listings_list,
        total=result.total_count,
        offset=offset,
        limit=limit,
        has_more=offset + len(result.listings_list) < result.total_count,
    )


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
    user: UserProfile = Depends(get_current_user),
) -> LeaderboardResponse:
    """
    Get marketplace leaderboard.

    v3.0.0: Now uses GetLeaderboardHandler (CQRS pattern).

    Only includes approved + public + not deleted listings.

    Args:
        period: 'monthly' | 'all_time'
        type: 'all' | 'project' | 'asset'

    Returns:
        Top listings by usage_count
    """
    container = get_container()
    handler = await container.get_leaderboard_handler()

    query = GetLeaderboardQuery(
        period=period,
        board_type=type,
        limit=10,
    )

    result = await handler.handle(query)

    if not result.success:
        logger.error(f"Failed to get leaderboard: {result.error}")
        raise HTTPException(500, "Failed to get leaderboard")

    return LeaderboardResponse(
        items=result.items,
        period=period,
        type=type,
    )


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
    user: UserProfile = Depends(get_current_user),
) -> ReportResponse:
    """
    Submit a content report for a marketplace listing.

    v3.0.0: Now uses CreateReportHandler (CQRS pattern) with SupportService.

    Users can report listings for copyright violations, inappropriate content, etc.

    Args:
        req: Report request with listing_id and reason

    Returns:
        Report confirmation with report_id

    Raises:
        HTTPException: 400 if already reported, 500 if failed
    """
    container = get_container()
    handler = await container.get_create_report_handler()

    command = CreateReportCommand(
        user_id=user.user_id,
        listing_id=req.listing_id,
        reason=req.reason,
    )

    result = await handler.handle(command)

    if not result.success:
        error_msg = result.error or ""
        # M-HIGH-003 fix: Only expose safe error messages
        if "already reported" in error_msg.lower():
            raise HTTPException(400, "You have already reported this listing")
        # Don't expose internal error details
        logger.error(f"Failed to submit report: {result.error}")
        raise HTTPException(500, "Failed to submit report")

    return ReportResponse(
        success=True,
        report_id=result.report_id,
        message=result.message,
    )


@router.get("/my-reports")
async def get_my_reports(
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100),
    user: UserProfile = Depends(get_current_user),
) -> MyReportsResponse:
    """
    Get reports submitted by the current user.

    v3.0.0: Now uses GetMyReportsHandler (CQRS pattern) with SupportService.

    Args:
        page: Page number (default: 1)
        limit: Items per page (default: 20)

    Returns:
        List of user's reports
    """
    container = get_container()
    handler = await container.get_my_reports_handler()

    query = GetMyReportsQuery(
        user_id=user.user_id,
        limit=limit,
        offset=offset,
    )

    result = await handler.handle(query)

    if not result.success:
        logger.error(f"Failed to get my reports: {result.error}")
        raise HTTPException(500, "Failed to get reports")

    return MyReportsResponse(
        items=result.items,
        total=result.total_count,
    )
