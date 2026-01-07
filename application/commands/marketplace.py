"""
Marketplace Commands - Listing operations that change state.

@module application.commands.marketplace
@version 1.0.0
"""

from dataclasses import dataclass
from typing import Optional, List

from domains.marketplace import (
    MarketplaceService,
    Listing,
    AssetCategory,
    PriceType,
)
from domains.billing import BillingService, TransactionType


@dataclass
class CreateListingCommand:
    """
    Command to create a new marketplace listing.
    """
    seller_id: str
    category: str  # AssetCategory value
    title: str
    description: Optional[str] = None
    price_type: str = "free"  # "free", "premium", "credits"
    credit_price: int = 0
    tags: Optional[List[str]] = None
    preview_url: Optional[str] = None
    seller_tier: str = "free"


@dataclass
class CreateListingResult:
    """Result of listing creation."""
    success: bool
    listing: Optional[Listing] = None
    error: Optional[str] = None


class CreateListingHandler:
    """Handler for CreateListingCommand."""

    def __init__(self, marketplace_service: MarketplaceService):
        self._marketplace_service = marketplace_service

    async def handle(self, command: CreateListingCommand) -> CreateListingResult:
        """Execute listing creation."""
        try:
            category = AssetCategory(command.category)
            price_type = PriceType(command.price_type)

            listing = await self._marketplace_service.create_listing(
                seller_id=command.seller_id,
                category=category,
                title=command.title,
                description=command.description,
                price_type=price_type,
                credit_price=command.credit_price,
                seller_tier=command.seller_tier,
            )

            # Update with additional metadata if provided
            if command.tags or command.preview_url:
                listing = await self._marketplace_service.update_listing(
                    listing_id=listing.listing_id,
                    user_id=command.seller_id,
                    tags=command.tags,
                    preview_url=command.preview_url,
                )

            return CreateListingResult(
                success=True,
                listing=listing,
            )

        except Exception as e:
            return CreateListingResult(
                success=False,
                error=str(e),
            )


@dataclass
class PurchaseListingCommand:
    """
    Command to purchase a marketplace listing.

    Coordinates between marketplace and billing domains.
    """
    listing_id: str
    buyer_id: str
    buyer_tier: str = "free"


@dataclass
class PurchaseListingResult:
    """Result of listing purchase."""
    success: bool
    listing: Optional[Listing] = None
    credits_spent: int = 0
    error: Optional[str] = None


class PurchaseListingHandler:
    """
    Handler for PurchaseListingCommand.

    This handler coordinates between marketplace and billing domains.
    """

    def __init__(
        self,
        marketplace_service: MarketplaceService,
        billing_service: BillingService
    ):
        self._marketplace_service = marketplace_service
        self._billing_service = billing_service

    async def handle(self, command: PurchaseListingCommand) -> PurchaseListingResult:
        """Execute listing purchase."""
        try:
            # Get listing details
            listing = await self._marketplace_service.get_listing(command.listing_id)
            if not listing:
                return PurchaseListingResult(
                    success=False,
                    error="Listing not found",
                )

            # Handle credit-based purchase
            if listing.requires_credits and listing.credit_price > 0:
                # Check if user can afford
                can_afford = await self._billing_service.check_can_afford(
                    command.buyer_id,
                    listing.credit_price
                )
                if not can_afford:
                    return PurchaseListingResult(
                        success=False,
                        error="Insufficient credits",
                    )

                # Deduct credits
                await self._billing_service.deduct_credits(
                    user_id=command.buyer_id,
                    amount=listing.credit_price,
                    tx_type=TransactionType.PURCHASE,
                    description=f"Purchase: {listing.title}",
                    idempotency_key=f"purchase_{command.listing_id}_{command.buyer_id}",
                )

            # Complete purchase in marketplace
            listing = await self._marketplace_service.purchase_listing(
                listing_id=command.listing_id,
                buyer_id=command.buyer_id,
                buyer_tier=command.buyer_tier,
            )

            return PurchaseListingResult(
                success=True,
                listing=listing,
                credits_spent=listing.credit_price if listing.requires_credits else 0,
            )

        except Exception as e:
            return PurchaseListingResult(
                success=False,
                error=str(e),
            )


@dataclass
class SubmitListingForReviewCommand:
    """Command to submit listing for review."""
    listing_id: str
    user_id: str


@dataclass
class SubmitListingForReviewResult:
    """Result of submission."""
    success: bool
    listing: Optional[Listing] = None
    error: Optional[str] = None


class SubmitListingForReviewHandler:
    """Handler for SubmitListingForReviewCommand."""

    def __init__(self, marketplace_service: MarketplaceService):
        self._marketplace_service = marketplace_service

    async def handle(self, command: SubmitListingForReviewCommand) -> SubmitListingForReviewResult:
        """Execute listing submission."""
        try:
            listing = await self._marketplace_service.submit_for_review(
                listing_id=command.listing_id,
                user_id=command.user_id,
            )

            return SubmitListingForReviewResult(
                success=True,
                listing=listing,
            )

        except Exception as e:
            return SubmitListingForReviewResult(
                success=False,
                error=str(e),
            )
