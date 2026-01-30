"""
Listing Repository Interface - Abstract data access for marketplace domain.

@module domains.marketplace.repository
@version 1.0.0

This defines the repository interface (port) for listing operations.
Concrete implementations live in infrastructure/repositories/.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from .aggregates.listing import Listing
from .value_objects import ListingStatus, AssetCategory, PriceType, ListingSortOrder, PriceFilter


class IListingRepository(ABC):
    """
    Repository interface for listing operations.

    Follows the Repository pattern from DDD.
    Infrastructure layer provides the concrete implementation.
    """

    @abstractmethod
    async def get_by_id(self, listing_id: str) -> Optional[Listing]:
        """
        Get listing by ID.

        Args:
            listing_id: Listing unique identifier

        Returns:
            Listing aggregate or None if not found
        """
        pass

    @abstractmethod
    async def get_by_ids(self, listing_ids: List[str]) -> List[Listing]:
        """
        Get multiple listings by IDs in a single query (batch fetch).

        WS-19: Added to fix N+1 queries in locked_elements check.

        Args:
            listing_ids: List of listing unique identifiers

        Returns:
            List of found Listing aggregates (may be fewer than requested if some not found)
        """
        pass

    @abstractmethod
    async def save(self, listing: Listing) -> Listing:
        """
        Persist listing.

        Creates new if not exists, updates if exists.

        Args:
            listing: Listing aggregate to save

        Returns:
            Saved Listing aggregate
        """
        pass

    @abstractmethod
    async def create(self, listing: Listing) -> Listing:
        """
        Create a new listing.

        Args:
            listing: Listing to create

        Returns:
            Created Listing
        """
        pass

    @abstractmethod
    async def update(self, listing: Listing) -> Listing:
        """
        Update existing listing.

        Args:
            listing: Listing to update

        Returns:
            Updated Listing
        """
        pass

    @abstractmethod
    async def delete(self, listing_id: str) -> bool:
        """
        Delete a listing.

        Args:
            listing_id: Listing ID to delete

        Returns:
            True if deleted
        """
        pass

    @abstractmethod
    async def get_by_seller(
        self,
        seller_id: str,
        status: Optional[ListingStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Listing]:
        """
        Get listings by seller.

        Args:
            seller_id: User ID of seller
            status: Filter by status
            limit: Maximum results
            offset: Results to skip

        Returns:
            List of Listings
        """
        pass

    @abstractmethod
    async def get_by_seller_with_count(
        self,
        seller_id: str,
        status: Optional[ListingStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Listing], int]:
        """
        Get listings by seller with total count.

        Args:
            seller_id: User ID of seller
            status: Filter by status
            limit: Maximum results
            offset: Results to skip

        Returns:
            Tuple of (List of Listings, total_count)
        """
        pass

    @abstractmethod
    async def get_published(
        self,
        category: Optional[AssetCategory] = None,
        price_type: Optional[PriceType] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Listing]:
        """
        Get published listings.

        Args:
            category: Filter by category
            price_type: Filter by price type
            tags: Filter by tags
            limit: Maximum results
            offset: Results to skip

        Returns:
            List of published Listings
        """
        pass

    @abstractmethod
    async def get_featured(self, limit: int = 10) -> List[Listing]:
        """
        Get featured listings.

        Args:
            limit: Maximum results

        Returns:
            List of featured Listings
        """
        pass

    @abstractmethod
    async def get_pending_review(self, limit: int = 50) -> List[Listing]:
        """
        Get listings pending review.

        Args:
            limit: Maximum results

        Returns:
            List of pending Listings
        """
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        category: Optional[AssetCategory] = None,
        price_type: Optional[PriceType] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Listing]:
        """
        Search listings.

        Args:
            query: Search query
            category: Filter by category
            price_type: Filter by price type
            limit: Maximum results
            offset: Results to skip

        Returns:
            List of matching Listings
        """
        pass

    @abstractmethod
    async def search_with_filters(
        self,
        query: str = "",
        category: Optional[AssetCategory] = None,
        price_filter: Optional[PriceFilter] = None,
        sort_by: ListingSortOrder = ListingSortOrder.LATEST,
        tier_filter: Optional[str] = None,
        featured: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Listing], int]:
        """
        Search listings with advanced filtering and sorting.

        Args:
            query: Search query (optional)
            category: Filter by category
            price_filter: Price filter (all/free/paid)
            sort_by: Sort order
            tier_filter: Filter by allowed tier
            featured: Prioritize featured listings
            limit: Maximum results
            offset: Results to skip

        Returns:
            Tuple of (List of Listings, total_count)
        """
        pass

    @abstractmethod
    async def get_popular(
        self,
        category: Optional[AssetCategory] = None,
        days: int = 30,
        limit: int = 50
    ) -> List[Listing]:
        """
        Get popular listings.

        Args:
            category: Filter by category
            days: Time window in days
            limit: Maximum results

        Returns:
            List of popular Listings
        """
        pass

    @abstractmethod
    async def record_purchase(
        self,
        listing_id: str,
        buyer_id: str,
        credit_amount: int = 0
    ) -> tuple[bool, bool]:
        """
        Record a purchase atomically.

        Uses ON CONFLICT to prevent race conditions where concurrent
        requests both pass has_purchased() check before either records.

        Args:
            listing_id: Listing ID
            buyer_id: Buyer user ID
            credit_amount: Credits spent

        Returns:
            tuple[bool, bool]: (success, already_existed)
            - (True, False): New purchase recorded successfully
            - (True, True): Purchase already existed (idempotent)
            - (False, False): Failed to record purchase
        """
        pass

    @abstractmethod
    async def has_purchased(
        self,
        listing_id: str,
        user_id: str
    ) -> bool:
        """
        Check if user has purchased listing.

        Args:
            listing_id: Listing ID
            user_id: User ID

        Returns:
            True if purchased
        """
        pass

    @abstractmethod
    async def get_user_purchases(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Listing]:
        """
        Get listings purchased by user.

        Args:
            user_id: User ID
            limit: Maximum results
            offset: Results to skip

        Returns:
            List of purchased Listings
        """
        pass

    @abstractmethod
    async def get_seller_info(self, seller_id: str) -> Optional[dict]:
        """
        Get seller profile info.

        Args:
            seller_id: Seller user ID

        Returns:
            Dict with username, avatar_url or None if not found
        """
        pass

    @abstractmethod
    async def get_listing_detail(
        self,
        listing_id: str,
        user_id: Optional[str] = None
    ) -> Optional[tuple[Listing, bool, Optional[dict]]]:
        """
        Get listing detail with access control, purchase status and seller info.

        Access rules:
        - Seller can always see their own listing
        - Others can only see: is_public=True AND is_deleted=False AND moderation_status='approved'

        Args:
            listing_id: Listing ID
            user_id: Optional user ID for access control and purchase check

        Returns:
            Tuple of (Listing, is_purchased, seller_info) or None if not accessible
        """
        pass
