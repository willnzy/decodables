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
)


@dataclass
class GetListingQuery:
    """Query to get a listing by ID."""
    listing_id: str


@dataclass
class GetListingResult:
    """Result of listing query."""
    success: bool
    listing: Optional[Listing] = None
    listing_dict: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class GetListingHandler:
    """Handler for GetListingQuery."""

    def __init__(self, marketplace_service: MarketplaceService):
        self._marketplace_service = marketplace_service

    async def handle(self, query: GetListingQuery) -> GetListingResult:
        """Execute listing query."""
        try:
            listing = await self._marketplace_service.get_listing(query.listing_id)

            if not listing:
                return GetListingResult(
                    success=False,
                    error="Listing not found",
                )

            return GetListingResult(
                success=True,
                listing=listing,
                listing_dict=listing.to_dict(),
            )

        except Exception as e:
            return GetListingResult(
                success=False,
                error=str(e),
            )


@dataclass
class SearchListingsQuery:
    """Query to search listings."""
    query: str
    category: Optional[str] = None
    price_type: Optional[str] = None
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
        """Execute listing search."""
        try:
            category = AssetCategory(query.category) if query.category else None
            price_type = PriceType(query.price_type) if query.price_type else None

            listings = await self._marketplace_service.search_listings(
                query=query.query,
                category=category,
                price_type=price_type,
                limit=query.limit,
                offset=query.offset,
            )

            return SearchListingsResult(
                success=True,
                listings=listings,
                listings_list=[l.to_dict() for l in listings],
                total_count=len(listings),
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
