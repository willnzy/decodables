"""
Marketplace Queries - Listing read operations.

@module application.queries.marketplace
@version 1.0.0
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from domains.marketplace import (
    MarketplaceService,
    Listing,
    AssetCategory,
    PriceType,
    ListingSortOrder,
    PriceFilter,
)


@dataclass
class GetListingQuery:
    """Query to get a listing by ID with optional access control."""
    listing_id: str
    user_id: Optional[str] = None  # For access control and is_purchased check


@dataclass
class GetListingResult:
    """Result of listing query."""
    success: bool
    listing: Optional[Listing] = None
    listing_dict: Optional[Dict[str, Any]] = None
    is_purchased: bool = False
    seller_info: Optional[Dict[str, Any]] = None  # username, avatar_url
    error: Optional[str] = None


class GetListingHandler:
    """Handler for GetListingQuery."""

    def __init__(self, marketplace_service: MarketplaceService):
        self._marketplace_service = marketplace_service

    async def handle(self, query: GetListingQuery) -> GetListingResult:
        """Execute listing query with access control."""
        try:
            # Use get_listing_detail for access control, purchase status, and seller info
            listing, is_purchased, seller_info = await self._marketplace_service.get_listing_detail(
                listing_id=query.listing_id,
                user_id=query.user_id,
            )

            if not listing:
                return GetListingResult(
                    success=False,
                    error="Listing not found",
                )

            # Build listing dict with additional fields
            listing_dict = listing.to_dict()
            listing_dict["is_purchased"] = is_purchased
            if seller_info:
                listing_dict["seller_username"] = seller_info.get("username")
                listing_dict["seller_avatar_url"] = seller_info.get("avatar_url")

            return GetListingResult(
                success=True,
                listing=listing,
                listing_dict=listing_dict,
                is_purchased=is_purchased,
                seller_info=seller_info,
            )

        except Exception as e:
            return GetListingResult(
                success=False,
                error=str(e),
            )


@dataclass
class SearchListingsQuery:
    """Query to search listings with filtering and sorting."""
    query: str = ""
    category: Optional[str] = None
    price_type: Optional[str] = None  # Deprecated: use price_filter instead
    price_filter: Optional[str] = None  # "all" | "t1" | "paid"
    sort_by: Optional[str] = None  # "latest" | "popular" | "price_asc" | "price_desc" | "best_selling"
    tier_filter: Optional[str] = None  # User tier filter
    featured: bool = False
    limit: int = 50
    offset: int = 0


@dataclass
class SearchListingsResult:
    """Result of listing search."""
    success: bool
    listings: List[Listing] = None
    listings_list: List[Dict[str, Any]] = None
    total_count: int = 0
    error: Optional[str] = None

    def __post_init__(self):
        if self.listings is None:
            self.listings = []
        if self.listings_list is None:
            self.listings_list = []


class SearchListingsHandler:
    """Handler for SearchListingsQuery."""

    def __init__(self, marketplace_service: MarketplaceService):
        self._marketplace_service = marketplace_service

    async def handle(self, query: SearchListingsQuery) -> SearchListingsResult:
        """Execute listing search with filtering and sorting."""
        try:
            # Convert string parameters to enums (with validation)
            category = None
            if query.category:
                try:
                    category = AssetCategory(query.category)
                except ValueError:
                    pass  # Invalid category, ignore filter

            sort_by = ListingSortOrder.LATEST  # Default
            if query.sort_by:
                try:
                    sort_by = ListingSortOrder(query.sort_by)
                except ValueError:
                    pass  # Invalid sort, use default

            price_filter = None
            # Support both old price_type and new price_filter
            filter_value = query.price_filter or query.price_type
            if filter_value:
                try:
                    price_filter = PriceFilter(filter_value)
                except ValueError:
                    pass  # Invalid filter, ignore

            # Use the enhanced search method
            listings, total_count = await self._marketplace_service.search_listings_with_filters(
                query=query.query,
                category=category,
                price_filter=price_filter,
                sort_by=sort_by,
                tier_filter=query.tier_filter,
                featured=query.featured,
                limit=query.limit,
                offset=query.offset,
            )

            return SearchListingsResult(
                success=True,
                listings=listings,
                listings_list=[l.to_dict() if hasattr(l, 'to_dict') else l for l in listings],
                total_count=total_count,
            )

        except Exception as e:
            return SearchListingsResult(
                success=False,
                error=str(e),
            )


@dataclass
class GetFeaturedListingsQuery:
    """Query to get featured listings."""
    limit: int = 10


@dataclass
class GetFeaturedListingsResult:
    """Result of featured listings query."""
    success: bool
    listings: List[Listing] = None
    listings_list: List[Dict[str, Any]] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.listings is None:
            self.listings = []
        if self.listings_list is None:
            self.listings_list = []


class GetFeaturedListingsHandler:
    """Handler for GetFeaturedListingsQuery."""

    def __init__(self, marketplace_service: MarketplaceService):
        self._marketplace_service = marketplace_service

    async def handle(self, query: GetFeaturedListingsQuery) -> GetFeaturedListingsResult:
        """Execute featured listings query."""
        try:
            listings = await self._marketplace_service.get_featured_listings(
                limit=query.limit
            )

            return GetFeaturedListingsResult(
                success=True,
                listings=listings,
                listings_list=[l.to_dict() for l in listings],
            )

        except Exception as e:
            return GetFeaturedListingsResult(
                success=False,
                error=str(e),
            )


@dataclass
class GetUserPurchasesQuery:
    """Query to get user's purchased listings."""
    user_id: str
    limit: int = 50
    offset: int = 0


@dataclass
class GetUserPurchasesResult:
    """Result of user purchases query."""
    success: bool
    listings: List[Listing] = None
    listings_list: List[Dict[str, Any]] = None
    total_count: int = 0
    error: Optional[str] = None

    def __post_init__(self):
        if self.listings is None:
            self.listings = []
        if self.listings_list is None:
            self.listings_list = []


class GetUserPurchasesHandler:
    """Handler for GetUserPurchasesQuery."""

    def __init__(self, marketplace_service: MarketplaceService):
        self._marketplace_service = marketplace_service

    async def handle(self, query: GetUserPurchasesQuery) -> GetUserPurchasesResult:
        """Execute user purchases query."""
        try:
            listings = await self._marketplace_service.get_user_purchases(
                user_id=query.user_id,
                limit=query.limit,
                offset=query.offset,
            )

            return GetUserPurchasesResult(
                success=True,
                listings=listings,
                listings_list=[l.to_dict() for l in listings],
                total_count=len(listings),
            )

        except Exception as e:
            return GetUserPurchasesResult(
                success=False,
                error=str(e),
            )


# ==========================================
# v3.0.0: New Queries for Architecture Consistency
# ==========================================

@dataclass
class GetMyListingsQuery:
    """Query to get seller's own listings."""
    seller_id: str
    status: Optional[str] = None  # Filter by status
    limit: int = 20
    offset: int = 0


@dataclass
class GetMyListingsResult:
    """Result of my listings query."""
    success: bool
    listings: List[Listing] = None
    listings_list: List[Dict[str, Any]] = None
    total_count: int = 0
    error: Optional[str] = None

    def __post_init__(self):
        if self.listings is None:
            self.listings = []
        if self.listings_list is None:
            self.listings_list = []


class GetMyListingsHandler:
    """Handler for GetMyListingsQuery."""

    def __init__(self, marketplace_service: MarketplaceService):
        self._marketplace_service = marketplace_service

    async def handle(self, query: GetMyListingsQuery) -> GetMyListingsResult:
        """Execute my listings query with count."""
        from domains.marketplace.value_objects import ListingStatus

        try:
            # Parse status filter
            status_filter = None
            if query.status:
                try:
                    status_filter = ListingStatus(query.status)
                except ValueError:
                    pass  # Invalid status, ignore filter

            # Get listings with total count
            listings, total_count = await self._marketplace_service.get_seller_listings_with_count(
                seller_id=query.seller_id,
                status=status_filter,
                limit=query.limit,
                offset=query.offset,
            )

            return GetMyListingsResult(
                success=True,
                listings=listings,
                listings_list=[l.to_dict() for l in listings],
                total_count=total_count,
            )

        except Exception as e:
            return GetMyListingsResult(
                success=False,
                error=str(e),
            )


@dataclass
class GetSellerStatsQuery:
    """Query to get seller statistics."""
    seller_id: str


@dataclass
class GetSellerStatsResult:
    """Result of seller stats query."""
    success: bool
    stats: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class GetSellerStatsHandler:
    """Handler for GetSellerStatsQuery."""

    def __init__(self, marketplace_service: MarketplaceService):
        self._marketplace_service = marketplace_service

    async def handle(self, query: GetSellerStatsQuery) -> GetSellerStatsResult:
        """Execute seller stats query."""
        try:
            stats = await self._marketplace_service.get_seller_stats(query.seller_id)

            return GetSellerStatsResult(
                success=True,
                stats=stats,
            )

        except Exception as e:
            return GetSellerStatsResult(
                success=False,
                error=str(e),
            )


@dataclass
class GetLeaderboardQuery:
    """Query to get marketplace leaderboard."""
    period: str = "monthly"  # "monthly" or "all_time"
    board_type: str = "all"  # "all", "project", or "asset"
    limit: int = 10


@dataclass
class GetLeaderboardResult:
    """Result of leaderboard query."""
    success: bool
    items: List[Dict[str, Any]] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.items is None:
            self.items = []


class GetLeaderboardHandler:
    """Handler for GetLeaderboardQuery."""

    def __init__(self, marketplace_service: MarketplaceService):
        self._marketplace_service = marketplace_service

    async def handle(self, query: GetLeaderboardQuery) -> GetLeaderboardResult:
        """Execute leaderboard query."""
        try:
            items = await self._marketplace_service.get_leaderboard(
                period=query.period,
                board_type=query.board_type,
                limit=query.limit,
            )

            return GetLeaderboardResult(
                success=True,
                items=items,
            )

        except Exception as e:
            return GetLeaderboardResult(
                success=False,
                error=str(e),
            )


@dataclass
class GetMyReportsQuery:
    """Query to get user's reports."""
    user_id: str
    page: int = 1
    limit: int = 20


@dataclass
class GetMyReportsResult:
    """Result of my reports query."""
    success: bool
    items: List[Dict[str, Any]] = None
    total_count: int = 0
    error: Optional[str] = None

    def __post_init__(self):
        if self.items is None:
            self.items = []


class GetMyReportsHandler:
    """Handler for GetMyReportsQuery."""

    def __init__(self, support_service):
        """
        Initialize handler with SupportService.

        Args:
            support_service: SupportService instance
        """
        self._support_service = support_service

    async def handle(self, query: GetMyReportsQuery) -> GetMyReportsResult:
        """Execute my reports query."""
        try:
            reports, total_count = await self._support_service.get_user_reports(
                user_id=query.user_id,
                page=query.page,
                limit=query.limit,
            )

            return GetMyReportsResult(
                success=True,
                items=reports,
                total_count=total_count,
            )

        except Exception as e:
            return GetMyReportsResult(
                success=False,
                error=str(e),
            )
