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
from .value_objects import (
    ListingStatus,
    ResourceType,
    AssetCategory,
    ListingSource,
    PriceType,
    ListingMetadata,
    ListingSortOrder,
    PriceFilter,
)
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

    async def save_listing(self, listing: Listing) -> Listing:
        """
        Persist a listing that has been modified in-memory.

        Used by application handlers after calling aggregate methods
        (e.g., set_pricing, set allowed_tiers).

        Args:
            listing: Modified listing to persist

        Returns:
            Persisted listing
        """
        return await self._repository.update(listing)

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
        resource_type: ResourceType,
        category: AssetCategory,
        title: str,
        description: Optional[str] = None,
        source: ListingSource = ListingSource.USER,
        price_type: PriceType = PriceType.FREE,
        credit_price: int = 0,
        allowed_tiers: Optional[List[str]] = None,
        seller_tier: str = "t1"
    ) -> Listing:
        """
        Create a new listing.

        Args:
            seller_id: User ID of seller
            resource_type: Resource type (asset or project)
            category: Asset category (specific content type)
            title: Listing title
            description: Optional description
            source: Asset source (system, user, ai, community)
            price_type: Pricing model
            credit_price: Price in credits
            allowed_tiers: List of tiers that can access this listing
            seller_tier: Seller's subscription tier

        Returns:
            Created Listing

        Raises:
            ListingAccessDeniedException: If seller can't publish
            InvalidListingDataException: If data invalid
        """
        # Only t2+ can publish to marketplace
        if seller_tier not in ("t2", "t3"):
            raise ListingAccessDeniedException(
                listing_id="new",
                user_id=seller_id,
                action="create listing (requires Starter or Pro tier)"
            )

        if not title or not title.strip():
            raise InvalidListingDataException("title", "Title is required")

        # Validate category matches resource_type
        if resource_type == ResourceType.PROJECT and not category.is_project_category:
            # For projects, default to TEMPLATE if invalid category provided
            category = AssetCategory.TEMPLATE

        listing = Listing.create_new(
            seller_id=seller_id,
            resource_type=resource_type,
            category=category,
            title=title.strip(),
            description=description,
            source=source,
            price_type=price_type,
            credit_price=credit_price,
            allowed_tiers=allowed_tiers,
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
    ) -> tuple[Listing, bool]:
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
            Tuple of (Updated Listing, requires_remoderation)
        """
        listing = await self.get_listing_or_raise(listing_id)

        if listing.seller_id != user_id:
            raise ListingAccessDeniedException(listing_id, user_id, "edit")

        requires_remoderation = listing.update_metadata(
            title=title,
            description=description,
            tags=tags,
            preview_url=preview_url,
        )

        updated_listing = await self._repository.update(listing)
        return updated_listing, requires_remoderation

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
        buyer_tier: str = "t1"
    ) -> Listing:
        """
        Purchase a listing.

        Note: For credit-based purchases, the PurchaseListingHandler in
        application layer handles the full flow including credit deduction
        and atomic purchase recording. This method is primarily used for
        free/premium assets that don't involve credit transactions.

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

        # Self-purchase guard (WS-M2: 4i#3, 1b#3)
        if listing.seller_id == buyer_id:
            raise PurchaseFailedException(
                listing_id, buyer_id, "Cannot purchase your own listing"
            )

        # Check if already purchased
        if await self._repository.has_purchased(listing_id, buyer_id):
            raise AlreadyPurchasedException(listing_id, buyer_id)

        # Free assets don't need payment
        if listing.is_free:
            success, already_existed = await self._repository.record_purchase(listing_id, buyer_id, 0)
            if not success:
                raise PurchaseFailedException(listing_id, buyer_id, "Failed to record purchase")
            if already_existed:
                raise AlreadyPurchasedException(listing_id, buyer_id)
            listing.record_download()
            return await self._repository.update(listing)

        # Premium assets require subscription
        if listing.requires_premium:
            if buyer_tier not in ("t2", "t3"):
                raise PurchaseFailedException(
                    listing_id, buyer_id,
                    "Premium subscription required"
                )
            success, already_existed = await self._repository.record_purchase(listing_id, buyer_id, 0)
            if not success:
                raise PurchaseFailedException(listing_id, buyer_id, "Failed to record purchase")
            if already_existed:
                raise AlreadyPurchasedException(listing_id, buyer_id)
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

    async def search_listings_with_filters(
        self,
        query: str = "",
        resource_type: Optional[str] = None,
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
            resource_type: Top-level filter ("asset" or "project")
            category: Filter by specific category (clipart, sticker, template, etc.)
            price_filter: Price filter (all/free/paid)
            sort_by: Sort order (latest/popular/price_asc/price_desc/best_selling)
            tier_filter: Filter by allowed tier
            featured: If True, prioritize featured listings
            limit: Max results
            offset: Results to skip

        Returns:
            Tuple of (List of Listings, total_count)
        """
        return await self._repository.search_with_filters(
            query=query,
            resource_type=resource_type,
            category=category,
            price_filter=price_filter,
            sort_by=sort_by,
            tier_filter=tier_filter,
            featured=featured,
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

    async def get_seller_listings_with_count(
        self,
        seller_id: str,
        status: Optional[ListingStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Listing], int]:
        """
        Get listings by seller with total count.

        Args:
            seller_id: Seller user ID
            status: Filter by status
            limit: Max results
            offset: Results to skip

        Returns:
            Tuple of (List of Listings, total_count)
        """
        return await self._repository.get_by_seller_with_count(
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

    async def get_listing_detail(
        self,
        listing_id: str,
        user_id: Optional[str] = None
    ) -> tuple[Optional[Listing], bool, Optional[dict]]:
        """
        Get listing detail with access control.

        Access rules:
        - Seller can always see their own listing
        - Others can only see: is_public=True AND is_deleted=False AND moderation_status='approved'

        Args:
            listing_id: Listing ID
            user_id: Optional user ID for access control and purchase check

        Returns:
            Tuple of (Listing or None, is_purchased, seller_info)
        """
        result = await self._repository.get_listing_detail(listing_id, user_id)

        if not result:
            return None, False, None

        return result

    async def unpublish_listing(
        self,
        listing_id: str,
        user_id: str
    ) -> Listing:
        """
        Unpublish a listing (back to draft for re-submission).

        Only the seller can unpublish their own listing.
        Only published listings can be unpublished.

        Args:
            listing_id: Listing ID
            user_id: User making the request

        Returns:
            Draft Listing (ready for re-submission)

        Raises:
            ListingNotFoundException: If listing not found
            ListingAccessDeniedException: If user is not the seller
            ValueError: If listing is not published
        """
        listing = await self.get_listing_or_raise(listing_id)

        if listing.seller_id != user_id:
            raise ListingAccessDeniedException(listing_id, user_id, "unpublish")

        if listing.status != ListingStatus.PUBLISHED:
            raise ValueError(f"Cannot unpublish listing in {listing.status.value} status")

        listing.unpublish()
        return await self._repository.update(listing)

    async def has_purchased(self, listing_id: str, user_id: str) -> bool:
        """
        Check if user has already purchased a listing.

        Args:
            listing_id: Listing ID
            user_id: User ID

        Returns:
            True if purchased
        """
        return await self._repository.has_purchased(listing_id, user_id)

    async def record_purchase(
        self,
        listing_id: str,
        buyer_id: str,
        credit_amount: int = 0
    ) -> tuple[bool, bool]:
        """
        Record a purchase atomically.

        Args:
            listing_id: Listing ID
            buyer_id: Buyer user ID
            credit_amount: Credits spent

        Returns:
            tuple[bool, bool]: (success, already_existed)
        """
        return await self._repository.record_purchase(
            listing_id=listing_id,
            buyer_id=buyer_id,
            credit_amount=credit_amount,
        )

    async def get_seller_stats(self, seller_id: str) -> dict:
        """
        Get seller statistics.

        Args:
            seller_id: Seller user ID

        Returns:
            Dict with total_earned_credits, listings_count, total_sales, total_usage
        """
        return await self._repository.get_seller_stats(seller_id)

    async def get_leaderboard(
        self,
        period: str = "monthly",
        board_type: str = "all",
        limit: int = 10
    ) -> list:
        """
        Get marketplace leaderboard.

        Args:
            period: 'monthly' or 'all_time'
            board_type: 'all', 'project', or 'asset'
            limit: Max results

        Returns:
            List of top listings
        """
        return await self._repository.get_leaderboard(period, board_type, limit)
