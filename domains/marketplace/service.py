"""
Marketplace Domain Service - Orchestrates listing operations.

@module domains.marketplace.service
@version 1.0.0

This service handles domain logic that doesn't naturally belong to aggregates.
It coordinates operations but delegates persistence to the repository.
"""

from typing import Optional, List

from .aggregates.listing import Listing
from .repository import IListingRepository
from .value_objects import ListingStatus, AssetCategory, PriceType, ListingMetadata
from .exceptions import (
    ListingNotFoundException,
    ListingAccessDeniedException,
    InvalidListingDataException,
    PurchaseFailedException,
    ListingNotPublishedException,
    AlreadyPurchasedException,
)


class MarketplaceService:
    """
    Domain service for marketplace operations.

    This service:
    - Manages listing lifecycle
    - Handles purchases
    - Enforces access rules
    """

    def __init__(self, repository: IListingRepository):
        """
        Initialize marketplace service with repository.

        Args:
            repository: Listing repository implementation
        """
        self._repository = repository

    async def get_listing(self, listing_id: str) -> Optional[Listing]:
        """
        Get listing by ID.

        Args:
            listing_id: Listing ID

        Returns:
            Listing or None
        """
        return await self._repository.get_by_id(listing_id)

    async def get_listing_or_raise(self, listing_id: str) -> Listing:
        """
        Get listing or raise exception.

        Args:
            listing_id: Listing ID

        Returns:
            Listing

        Raises:
            ListingNotFoundException: If not found
        """
        listing = await self._repository.get_by_id(listing_id)
        if not listing:
            raise ListingNotFoundException(listing_id)
        return listing

    async def create_listing(
        self,
        seller_id: str,
        category: AssetCategory,
        title: str,
        description: Optional[str] = None,
        price_type: PriceType = PriceType.FREE,
        credit_price: int = 0,
        seller_tier: str = "free"
    ) -> Listing:
        """
        Create a new listing.

        Args:
            seller_id: User ID of seller
            category: Asset category
            title: Listing title
            description: Optional description
            price_type: Pricing model
            credit_price: Price in credits
            seller_tier: Seller's subscription tier

        Returns:
            Created Listing

        Raises:
            ListingAccessDeniedException: If seller can't publish
            InvalidListingDataException: If data invalid
        """
        # Only starter+ can publish to marketplace
        if seller_tier not in ("starter", "pro"):
            raise ListingAccessDeniedException(
                listing_id="new",
                user_id=seller_id,
                action="create listing (requires Starter or Pro tier)"
            )

        if not title or not title.strip():
            raise InvalidListingDataException("title", "Title is required")

        listing = Listing.create_new(
            seller_id=seller_id,
            category=category,
            title=title.strip(),
            description=description,
            price_type=price_type,
            credit_price=credit_price,
        )

        return await self._repository.create(listing)

    async def update_listing(
        self,
        listing_id: str,
        user_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        preview_url: Optional[str] = None
    ) -> Listing:
        """
        Update listing metadata.

        Args:
            listing_id: Listing ID
            user_id: User making update
            title: New title
            description: New description
            tags: New tags
            preview_url: New preview URL

        Returns:
            Updated Listing
        """
        listing = await self.get_listing_or_raise(listing_id)

        if listing.seller_id != user_id:
            raise ListingAccessDeniedException(listing_id, user_id, "edit")

        listing.update_metadata(
            title=title,
            description=description,
            tags=tags,
            preview_url=preview_url,
        )

        return await self._repository.update(listing)

    async def submit_for_review(
        self,
        listing_id: str,
        user_id: str
    ) -> Listing:
        """
        Submit listing for review.

        Args:
            listing_id: Listing ID
            user_id: User submitting

        Returns:
            Updated Listing
        """
        listing = await self.get_listing_or_raise(listing_id)

        if listing.seller_id != user_id:
            raise ListingAccessDeniedException(listing_id, user_id, "submit")

        listing.submit_for_review()
        return await self._repository.update(listing)

    async def approve_listing(self, listing_id: str) -> Listing:
        """
        Approve and publish listing (admin only).

        Args:
            listing_id: Listing ID

        Returns:
            Published Listing
        """
        listing = await self.get_listing_or_raise(listing_id)
        listing.approve()
        return await self._repository.update(listing)

    async def reject_listing(
        self,
        listing_id: str,
        reason: str
    ) -> Listing:
        """
        Reject listing (admin only).

        Args:
            listing_id: Listing ID
            reason: Rejection reason

        Returns:
            Rejected Listing
        """
        listing = await self.get_listing_or_raise(listing_id)
        listing.reject(reason)
        return await self._repository.update(listing)

    async def purchase_listing(
        self,
        listing_id: str,
        buyer_id: str,
        buyer_tier: str = "free"
    ) -> Listing:
        """
        Purchase a listing.

        Args:
            listing_id: Listing ID
            buyer_id: Buyer user ID
            buyer_tier: Buyer's subscription tier

        Returns:
            Purchased Listing

        Raises:
            ListingNotPublishedException: If not published
            AlreadyPurchasedException: If already owned
            PurchaseFailedException: If purchase fails
        """
        listing = await self.get_listing_or_raise(listing_id)

        if not listing.is_published:
            raise ListingNotPublishedException(listing_id)

        # Check if already purchased
        if await self._repository.has_purchased(listing_id, buyer_id):
            raise AlreadyPurchasedException(listing_id, buyer_id)

        # Free assets don't need payment
        if listing.is_free:
            await self._repository.record_purchase(listing_id, buyer_id, 0)
            listing.record_download()
            return await self._repository.update(listing)

        # Premium assets require subscription
        if listing.requires_premium:
            if buyer_tier not in ("starter", "pro"):
                raise PurchaseFailedException(
                    listing_id, buyer_id,
                    "Premium subscription required"
                )
            await self._repository.record_purchase(listing_id, buyer_id, 0)
            listing.record_download()
            return await self._repository.update(listing)

        # Credit purchases are handled by the application layer
        # (which will coordinate with billing domain)
        return listing

    async def get_published_listings(
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
            limit: Max results
            offset: Results to skip

        Returns:
            List of Listings
        """
        return await self._repository.get_published(
            category=category,
            price_type=price_type,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    async def get_featured_listings(self, limit: int = 10) -> List[Listing]:
        """
        Get featured listings.

        Args:
            limit: Max results

        Returns:
            List of featured Listings
        """
        return await self._repository.get_featured(limit)

    async def search_listings(
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
            limit: Max results
            offset: Results to skip

        Returns:
            List of matching Listings
        """
        return await self._repository.search(
            query=query,
            category=category,
            price_type=price_type,
            limit=limit,
            offset=offset,
        )

    async def get_seller_listings(
        self,
        seller_id: str,
        status: Optional[ListingStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Listing]:
        """
        Get listings by seller.

        Args:
            seller_id: Seller user ID
            status: Filter by status
            limit: Max results
            offset: Results to skip

        Returns:
            List of Listings
        """
        return await self._repository.get_by_seller(
            seller_id=seller_id,
            status=status,
            limit=limit,
            offset=offset,
        )

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
            limit: Max results
            offset: Results to skip

        Returns:
            List of purchased Listings
        """
        return await self._repository.get_user_purchases(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )
