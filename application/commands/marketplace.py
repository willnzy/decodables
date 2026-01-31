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
    ResourceType,
    AssetCategory,
    ListingSource,
    PriceType,
)
from domains.billing import BillingService, TransactionType, CreditBucket


@dataclass
class CreateListingCommand:
    """
    Command to create a new marketplace listing.

    Supports two-level classification:
    - resource_type: "asset" or "project" (top-level)
    - category: specific content type (second-level)
    """
    seller_id: str
    resource_type: str = "asset"  # ResourceType value: "asset" or "project"
    category: str = "element"  # AssetCategory value
    title: str = ""
    description: Optional[str] = None
    source: str = "user"  # ListingSource value: "system", "user", "ai", "community"
    price_type: str = "free"  # "free", "subscription", "credits"
    credit_price: int = 0
    allowed_tiers: Optional[List[str]] = None  # ["t1", "t2", "t3"]
    tags: Optional[List[str]] = None
    preview_url: Optional[str] = None
    seller_tier: str = "t1"
    resource_id: Optional[str] = None  # Project/Asset ID to link back


@dataclass
class CreateListingResult:
    """Result of listing creation."""
    success: bool
    listing: Optional[Listing] = None
    error: Optional[str] = None


class CreateListingHandler:
    """Handler for CreateListingCommand."""

    def __init__(self, marketplace_service: MarketplaceService, supabase_client=None):
        self._marketplace_service = marketplace_service
        self._client = supabase_client  # For updating project link

    async def handle(self, command: CreateListingCommand) -> CreateListingResult:
        """Execute listing creation."""
        try:
            # Parse enums with validation
            try:
                resource_type = ResourceType(command.resource_type)
            except ValueError:
                resource_type = ResourceType.ASSET

            try:
                category = AssetCategory(command.category)
            except ValueError:
                # Default based on resource_type
                category = AssetCategory.TEMPLATE if resource_type == ResourceType.PROJECT else AssetCategory.ELEMENT

            try:
                source = ListingSource(command.source)
            except ValueError:
                source = ListingSource.USER

            price_type = PriceType(command.price_type)

            listing = await self._marketplace_service.create_listing(
                seller_id=command.seller_id,
                resource_type=resource_type,
                category=category,
                title=command.title,
                description=command.description,
                source=source,
                price_type=price_type,
                credit_price=command.credit_price,
                allowed_tiers=command.allowed_tiers,
                seller_tier=command.seller_tier,
            )

            # Update with additional metadata if provided
            if command.tags or command.preview_url:
                listing, _ = await self._marketplace_service.update_listing(
                    listing_id=listing.listing_id,
                    user_id=command.seller_id,
                    tags=command.tags,
                    preview_url=command.preview_url,
                )

            # v3.30: Auto-submit for review after creation (if preview_url is set)
            if listing.metadata.preview_url:
                listing = await self._marketplace_service.submit_for_review(
                    listing_id=listing.listing_id,
                    user_id=command.seller_id,
                )

            # Link project/asset to the new listing (bidirectional relationship)
            if command.resource_id and self._client:
                if resource_type == ResourceType.PROJECT:
                    # Get the listing's UUID
                    listing_result = await self._client.table("marketplace_listings").select(
                        "id"
                    ).eq("listing_id", listing.listing_id).single().execute()

                    if listing_result.data:
                        listing_uuid = listing_result.data["id"]

                        # v3.31: Fix bidirectional link
                        # 1. Update marketplace_listings.resource_id (for Selling view queries)
                        await self._client.table("marketplace_listings").update({
                            "resource_id": command.resource_id,
                        }).eq("listing_id", listing.listing_id).execute()

                        # 2. Update project with marketplace_listing_id
                        await self._client.table("projects").update({
                            "marketplace_listing_id": listing_uuid,
                            "listing_status": "pending",
                        }).eq("id", command.resource_id).execute()

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
class UpdateListingCommand:
    """
    Command to update a marketplace listing.

    Only editable in draft/rejected status.
    Set submit_for_review=True to also submit for review after update.
    """
    listing_id: str
    user_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    price_credits: Optional[int] = None
    allowed_tiers: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    preview_url: Optional[str] = None
    submit_for_review: bool = False  # Explicit flag to trigger auto-submit for DRAFT listings


@dataclass
class UpdateListingResult:
    """Result of listing update."""
    success: bool
    listing: Optional[Listing] = None
    requires_resubmit: bool = False
    error: Optional[str] = None


class UpdateListingHandler:
    """Handler for UpdateListingCommand."""

    def __init__(self, marketplace_service: MarketplaceService, supabase_client=None):
        self._marketplace_service = marketplace_service
        self._client = supabase_client  # For updating project link

    async def handle(self, command: UpdateListingCommand) -> UpdateListingResult:
        """Execute listing update."""
        try:
            requires_resubmit = False

            # Update metadata (title, description, tags, preview_url)
            # Returns (listing, requires_remoderation)
            listing, metadata_requires_remod = await self._marketplace_service.update_listing(
                listing_id=command.listing_id,
                user_id=command.user_id,
                title=command.title,
                description=command.description,
                tags=command.tags,
                preview_url=command.preview_url,
            )

            if metadata_requires_remod:
                requires_resubmit = True

            # Handle pricing update if provided
            # For published listings, changing price triggers re-moderation
            if command.price_credits is not None:
                price_type = PriceType.FREE if command.price_credits == 0 else PriceType.CREDITS
                pricing_requires_remod = listing.set_pricing(price_type, command.price_credits)
                listing = await self._marketplace_service.save_listing(listing)
                if pricing_requires_remod:
                    requires_resubmit = True

            # Handle allowed_tiers update if provided
            if command.allowed_tiers is not None:
                listing.allowed_tiers = command.allowed_tiers
                listing = await self._marketplace_service.save_listing(listing)

            # Auto-submit DRAFT listings for review when explicitly requested
            # or when preview_url is set (backward compatibility)
            from domains.marketplace.value_objects import ListingStatus
            should_submit = (
                listing.status == ListingStatus.DRAFT and
                (command.submit_for_review or listing.metadata.preview_url)
            )
            if should_submit:
                # Validate preview_url is required for publishing
                if not listing.metadata.preview_url:
                    return UpdateListingResult(
                        success=False,
                        error="Preview image is required to publish listing",
                    )
                await self._marketplace_service.submit_for_review(
                    listing_id=listing.listing_id,
                    user_id=command.user_id,
                )
                # Refresh listing to get updated status
                listing = await self._marketplace_service.get_listing(listing.listing_id)
                requires_resubmit = True

            # Update linked project's listing_status if re-moderation was triggered
            if requires_resubmit and self._client:
                try:
                    # Get the resource_id from the listing
                    listing_data = await self._client.table("marketplace_listings").select(
                        "resource_id"
                    ).eq("listing_id", listing.listing_id).single().execute()

                    if listing_data.data and listing_data.data.get("resource_id"):
                        # Update project's listing_status to pending
                        await self._client.table("projects").update({
                            "listing_status": "pending",
                        }).eq("id", listing_data.data["resource_id"]).execute()
                except Exception as e:
                    # Log but don't fail - listing update is the primary operation
                    import logging
                    logging.getLogger(__name__).warning(
                        f"Failed to update project listing_status: {e}"
                    )

            return UpdateListingResult(
                success=True,
                listing=listing,
                requires_resubmit=requires_resubmit,
            )

        except ValueError as e:
            # Catch "Cannot edit" errors from aggregate
            return UpdateListingResult(
                success=False,
                error=str(e),
            )
        except Exception as e:
            return UpdateListingResult(
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
    buyer_tier: str = "t1"


@dataclass
class PurchaseListingResult:
    """Result of listing purchase."""
    success: bool
    listing: Optional[Listing] = None
    credits_spent: int = 0
    already_owned: bool = False
    project_id: Optional[str] = None
    error: Optional[str] = None


class PurchaseListingHandler:
    """
    Handler for PurchaseListingCommand.

    This handler coordinates between marketplace and billing domains.

    Security improvements (v2.1.0):
    - M-P0-001: Uses atomic record_purchase with ON CONFLICT to prevent race conditions
    - M-P0-002: Refunds credits if purchase recording fails after deduction
    - M-P0-003: Re-validates listing status before completing purchase
    """

    def __init__(
        self,
        marketplace_service: MarketplaceService,
        billing_service: BillingService
    ):
        self._marketplace_service = marketplace_service
        self._billing_service = billing_service

    async def handle(self, command: PurchaseListingCommand) -> PurchaseListingResult:
        """
        Execute listing purchase with atomic guarantees.

        Flow:
        1. Validate listing exists and is published
        2. Check tier access
        3. Check if already purchased (early exit)
        4. Deduct credits (if required)
        5. Record purchase atomically (handles race condition)
        6. If recording fails after deduction, refund credits
        """
        from domains.marketplace.exceptions import (
            ListingNotFoundException,
            AlreadyPurchasedException,
            PurchaseFailedException,
            ListingNotPublishedException,
        )
        from domains.marketplace.value_objects import ListingStatus
        import logging

        logger = logging.getLogger(__name__)
        credits_deducted = False
        credits_to_deduct = 0
        listing = None

        try:
            # Step 1: Get and validate listing
            listing = await self._marketplace_service.get_listing(command.listing_id)
            if not listing:
                return PurchaseListingResult(
                    success=False,
                    error="Listing not found",
                )

            # M-P0-003: Validate listing is still published
            if listing.status != ListingStatus.PUBLISHED:
                return PurchaseListingResult(
                    success=False,
                    error="Listing is not available for purchase",
                )

            # Step 2: Check tier access (M-HIGH-004: verified against listing data)
            if command.buyer_tier.lower() not in [t.lower() for t in listing.allowed_tiers]:
                return PurchaseListingResult(
                    success=False,
                    error=f"Tier access denied. This listing requires: {', '.join(listing.allowed_tiers)}",
                )

            # Step 3: Check if already purchased (early exit, not authoritative)
            try:
                if await self._marketplace_service.has_purchased(
                    command.listing_id, command.buyer_id
                ):
                    return PurchaseListingResult(
                        success=True,
                        listing=listing,
                        credits_spent=0,
                        already_owned=True,
                    )
            except Exception as e:
                # has_purchased now raises on DB errors - fail safely
                logger.error(f"Failed to check purchase status: {e}")
                return PurchaseListingResult(
                    success=False,
                    error="Unable to verify purchase status. Please try again.",
                )

            # Step 4: Handle credit-based purchase
            if listing.requires_credits and listing.credit_price > 0:
                credits_to_deduct = listing.credit_price

                # Check if user can afford
                can_afford = await self._billing_service.check_can_afford(
                    command.buyer_id,
                    credits_to_deduct
                )
                if not can_afford:
                    return PurchaseListingResult(
                        success=False,
                        error="Insufficient credits",
                    )

                # Deduct credits with idempotency key
                idempotency_key = f"purchase_{command.listing_id}_{command.buyer_id}"
                await self._billing_service.deduct_credits(
                    user_id=command.buyer_id,
                    amount=credits_to_deduct,
                    tx_type=TransactionType.PURCHASE,
                    description=f"Purchase: {listing.metadata.title}",
                    idempotency_key=idempotency_key,
                )
                credits_deducted = True

            # Step 5: Record purchase atomically (M-P0-001 fix)
            # This handles race condition where concurrent requests both pass has_purchased()
            success, already_existed = await self._marketplace_service.record_purchase(
                listing_id=command.listing_id,
                buyer_id=command.buyer_id,
                credit_amount=credits_to_deduct,
            )

            if not success:
                # M-P0-002: Refund credits if purchase recording failed
                if credits_deducted and credits_to_deduct > 0:
                    try:
                        await self._billing_service.add_credits(
                            user_id=command.buyer_id,
                            amount=credits_to_deduct,
                            bucket=CreditBucket.PERMANENT,
                            tx_type=TransactionType.REFUND,
                            description=f"Refund: Failed purchase of {listing.metadata.title}",
                            idempotency_key=f"refund_{command.listing_id}_{command.buyer_id}",
                        )
                        logger.info(f"Refunded {credits_to_deduct} credits to user {command.buyer_id} after failed purchase")
                    except Exception as refund_err:
                        # Critical: Log for manual intervention
                        logger.critical(
                            f"CRITICAL: Failed to refund {credits_to_deduct} credits to user {command.buyer_id} "
                            f"for listing {command.listing_id}. Manual intervention required. Error: {refund_err}"
                        )

                return PurchaseListingResult(
                    success=False,
                    error="Failed to complete purchase. Please try again.",
                )

            # Handle race condition: another request completed the purchase first
            if already_existed:
                # M-P0-002: Refund credits since purchase was already recorded
                if credits_deducted and credits_to_deduct > 0:
                    try:
                        await self._billing_service.add_credits(
                            user_id=command.buyer_id,
                            amount=credits_to_deduct,
                            bucket=CreditBucket.PERMANENT,
                            tx_type=TransactionType.REFUND,
                            description=f"Refund: Duplicate purchase attempt for {listing.metadata.title}",
                            idempotency_key=f"refund_dup_{command.listing_id}_{command.buyer_id}",
                        )
                        logger.info(f"Refunded {credits_to_deduct} credits for duplicate purchase attempt")
                    except Exception as refund_err:
                        logger.critical(
                            f"CRITICAL: Failed to refund duplicate charge of {credits_to_deduct} credits "
                            f"to user {command.buyer_id}. Error: {refund_err}"
                        )

                return PurchaseListingResult(
                    success=True,
                    listing=listing,
                    credits_spent=0,
                    already_owned=True,
                )

            # Success: new purchase recorded
            return PurchaseListingResult(
                success=True,
                listing=listing,
                credits_spent=credits_to_deduct,
                already_owned=False,
                project_id=None,
            )

        except AlreadyPurchasedException:
            return PurchaseListingResult(
                success=True,
                listing=listing,
                credits_spent=0,
                already_owned=True,
            )
        except ListingNotFoundException:
            return PurchaseListingResult(
                success=False,
                error="Listing not found",
            )
        except ListingNotPublishedException:
            return PurchaseListingResult(
                success=False,
                error="Listing is not published",
            )
        except PurchaseFailedException as e:
            # M-P0-002: Refund on purchase failure
            if credits_deducted and credits_to_deduct > 0:
                try:
                    await self._billing_service.add_credits(
                        user_id=command.buyer_id,
                        amount=credits_to_deduct,
                        bucket=CreditBucket.PERMANENT,
                        tx_type=TransactionType.REFUND,
                        description=f"Refund: Purchase failed",
                        idempotency_key=f"refund_fail_{command.listing_id}_{command.buyer_id}",
                    )
                except Exception as refund_err:
                    logger.critical(
                        f"CRITICAL: Failed to refund {credits_to_deduct} credits after PurchaseFailedException. "
                        f"User: {command.buyer_id}, Listing: {command.listing_id}. Error: {refund_err}"
                    )
            return PurchaseListingResult(
                success=False,
                error=str(e),
            )
        except Exception as e:
            # M-P0-002: Refund on any unexpected failure
            if credits_deducted and credits_to_deduct > 0:
                try:
                    await self._billing_service.add_credits(
                        user_id=command.buyer_id,
                        amount=credits_to_deduct,
                        bucket=CreditBucket.PERMANENT,
                        tx_type=TransactionType.REFUND,
                        description=f"Refund: Unexpected error during purchase",
                        idempotency_key=f"refund_err_{command.listing_id}_{command.buyer_id}",
                    )
                except Exception as refund_err:
                    logger.critical(
                        f"CRITICAL: Failed to refund {credits_to_deduct} credits after unexpected error. "
                        f"User: {command.buyer_id}, Listing: {command.listing_id}. Error: {refund_err}"
                    )
            # Don't expose internal error details
            logger.error(f"Unexpected error during purchase: {e}")
            return PurchaseListingResult(
                success=False,
                error="An unexpected error occurred. Please try again.",
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


@dataclass
class UnpublishListingCommand:
    """Command to unpublish (archive) a listing."""
    listing_id: str
    user_id: str


@dataclass
class UnpublishListingResult:
    """Result of unpublish operation."""
    success: bool
    listing: Optional[Listing] = None
    error: Optional[str] = None


class UnpublishListingHandler:
    """Handler for UnpublishListingCommand."""

    def __init__(self, marketplace_service: MarketplaceService, supabase_client=None):
        self._marketplace_service = marketplace_service
        self._client = supabase_client  # For updating project link

    async def handle(self, command: UnpublishListingCommand) -> UnpublishListingResult:
        """Execute listing unpublish (back to draft)."""
        try:
            listing = await self._marketplace_service.unpublish_listing(
                listing_id=command.listing_id,
                user_id=command.user_id,
            )

            # Update linked project's listing_status to draft
            if self._client:
                try:
                    # Get the resource_id from the listing
                    listing_data = await self._client.table("marketplace_listings").select(
                        "resource_id"
                    ).eq("listing_id", listing.listing_id).single().execute()

                    if listing_data.data and listing_data.data.get("resource_id"):
                        # Update project's listing_status to draft
                        await self._client.table("projects").update({
                            "listing_status": "draft",
                        }).eq("id", listing_data.data["resource_id"]).execute()
                except Exception as e:
                    # Log but don't fail - listing unpublish is the primary operation
                    import logging
                    logging.getLogger(__name__).warning(
                        f"Failed to update project listing_status: {e}"
                    )

            return UnpublishListingResult(
                success=True,
                listing=listing,
            )

        except Exception as e:
            return UnpublishListingResult(
                success=False,
                error=str(e),
            )


# ==========================================
# v3.0.0: Support-related Commands
# ==========================================

@dataclass
class CreateReportCommand:
    """Command to create a marketplace content report."""
    user_id: str
    listing_id: str
    reason: str


@dataclass
class CreateReportResult:
    """Result of report creation."""
    success: bool
    report_id: Optional[str] = None
    message: str = ""
    error: Optional[str] = None


class CreateReportHandler:
    """Handler for CreateReportCommand."""

    def __init__(self, support_service):
        """
        Initialize handler with SupportService.

        Args:
            support_service: SupportService instance
        """
        self._support_service = support_service

    async def handle(self, command: CreateReportCommand) -> CreateReportResult:
        """Execute report creation."""
        from domains.support import ReportAlreadyExistsException

        try:
            report = await self._support_service.create_report(
                user_id=command.user_id,
                listing_id=command.listing_id,
                reason=command.reason,
            )

            if report:
                return CreateReportResult(
                    success=True,
                    report_id=report.get("id"),
                    message="Report submitted successfully",
                )

            return CreateReportResult(
                success=False,
                error="Failed to submit report",
            )

        except ReportAlreadyExistsException as e:
            return CreateReportResult(
                success=False,
                error=str(e),
            )
        except Exception as e:
            # Don't expose internal error details
            return CreateReportResult(
                success=False,
                error="Failed to submit report",
            )
