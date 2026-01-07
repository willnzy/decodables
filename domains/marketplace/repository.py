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
from .value_objects import ListingStatus, AssetCategory, PriceType


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
    ) -> bool:
        """
        Record a purchase.

        Args:
            listing_id: Listing ID
            buyer_id: Buyer user ID
            credit_amount: Credits spent

        Returns:
            True if recorded
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
