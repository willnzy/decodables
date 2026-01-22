"""
Listing Aggregate - Encapsulates marketplace listing management.

@module domains.marketplace.aggregates.listing
@version 1.0.0

This is the aggregate root for marketplace listing management.
All listing operations must go through this aggregate.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List

from ..value_objects import (
    ListingId,
    ListingStatus,
    ResourceType,
    AssetCategory,
    ListingSource,
    PriceType,
    ListingMetadata,
    ListingStats,
)


@dataclass
class Listing:
    """
    Aggregate root for marketplace listing management.

    Encapsulates:
    - Listing metadata
    - Pricing and availability
    - Statistics and engagement
    - Review status
    - Two-level classification (resource_type + category)
    - Access control (allowed_tiers)
    """
    listing_id: str
    seller_id: str
    resource_type: ResourceType  # Top-level: asset or project
    category: AssetCategory  # Second-level: specific content type
    metadata: ListingMetadata
    source: ListingSource = ListingSource.USER
    price_type: PriceType = PriceType.FREE
    credit_price: int = 0
    allowed_tiers: List[str] = field(default_factory=lambda: ["t1", "t2", "t3"])
    status: ListingStatus = ListingStatus.DRAFT
    stats: ListingStats = field(default_factory=ListingStats)
    is_featured: bool = False
    rejection_reason: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None

    @classmethod
    def create_new(
        cls,
        seller_id: str,
        resource_type: ResourceType,
        category: AssetCategory,
        title: str,
        description: Optional[str] = None,
        source: ListingSource = ListingSource.USER,
        price_type: PriceType = PriceType.FREE,
        credit_price: int = 0,
        allowed_tiers: Optional[List[str]] = None,
    ) -> "Listing":
        """
        Factory method to create a new listing.

        Args:
            seller_id: User ID of seller
            resource_type: Resource type (asset or project)
            category: Asset category (specific content type)
            title: Listing title
            description: Optional description
            source: Asset source (system, user, ai, community)
            price_type: Pricing model
            credit_price: Price in credits (if applicable)
            allowed_tiers: List of tiers that can access this listing

        Returns:
            New Listing instance
        """
        listing_id = ListingId.generate()

        return cls(
            listing_id=str(listing_id),
            seller_id=seller_id,
            resource_type=resource_type,
            category=category,
            metadata=ListingMetadata(title=title, description=description),
            source=source,
            price_type=price_type,
            credit_price=credit_price if price_type == PriceType.CREDITS else 0,
            allowed_tiers=allowed_tiers or ["t1", "t2", "t3"],
            status=ListingStatus.DRAFT,
        )

    @property
    def title(self) -> str:
        """Get listing title."""
        return self.metadata.title

    @property
    def is_published(self) -> bool:
        """Check if listing is published."""
        return self.status == ListingStatus.PUBLISHED

    @property
    def is_editable(self) -> bool:
        """Check if listing can be edited."""
        return self.status.is_editable

    @property
    def is_free(self) -> bool:
        """Check if listing is free."""
        return self.price_type == PriceType.FREE

    @property
    def requires_credits(self) -> bool:
        """Check if listing requires credits."""
        return self.price_type == PriceType.CREDITS

    @property
    def requires_premium(self) -> bool:
        """Check if listing requires premium subscription."""
        return self.price_type == PriceType.PREMIUM

    def can_access(self, user_id: str, user_tier: str = "t1") -> bool:
        """
        Check if user can access this listing.

        Args:
            user_id: User ID
            user_tier: User's subscription tier

        Returns:
            True if user can access
        """
        # Seller can always access
        if self.seller_id == user_id:
            return True
        # Must be published
        if not self.is_published:
            return False
        # Check tier restriction
        if user_tier not in self.allowed_tiers:
            return False
        # Free listings are accessible to allowed tiers
        if self.is_free:
            return True
        # Premium requires paid subscription
        if self.requires_premium and user_tier in ("t2", "t3"):
            return True
        return False

    def update_metadata(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        preview_url: Optional[str] = None
    ):
        """Update listing metadata."""
        if not self.is_editable:
            raise ValueError("Cannot edit published listing")

        if title is not None:
            self.metadata.title = title
        if description is not None:
            self.metadata.description = description
        if tags is not None:
            self.metadata.tags = tags
        if preview_url is not None:
            self.metadata.preview_url = preview_url
            # Also set thumbnail_url to the same value for marketplace display
            self.metadata.thumbnail_url = preview_url
        self.updated_at = datetime.utcnow()

    def set_pricing(self, price_type: PriceType, credit_price: int = 0) -> bool:
        """
        Set listing pricing.

        For published listings, changing price will trigger re-moderation.

        Args:
            price_type: Pricing model
            credit_price: Price in credits

        Returns:
            True if listing requires re-moderation, False otherwise
        """
        requires_remoderation = False

        # Check if editing is allowed
        if self.status == ListingStatus.PUBLISHED:
            # Published listings: allow edit but require re-moderation
            requires_remoderation = True
        elif not self.is_editable:
            # PENDING_REVIEW listings cannot be edited
            raise ValueError("Cannot edit listing in pending status")

        self.price_type = price_type
        self.credit_price = credit_price if price_type == PriceType.CREDITS else 0
        self.updated_at = datetime.utcnow()

        # Set back to pending for re-moderation if was published
        if requires_remoderation:
            self.status = ListingStatus.PENDING_REVIEW

        return requires_remoderation

    def submit_for_review(self):
        """Submit listing for review."""
        if self.status != ListingStatus.DRAFT:
            raise ValueError("Only draft listings can be submitted")

        if not self.metadata.preview_url:
            raise ValueError("Preview image is required")

        self.status = ListingStatus.PENDING_REVIEW
        self.updated_at = datetime.utcnow()

    def approve(self):
        """Approve and publish listing."""
        if self.status != ListingStatus.PENDING_REVIEW:
            raise ValueError("Only pending listings can be approved")

        self.status = ListingStatus.PUBLISHED
        self.published_at = datetime.utcnow()
        self.rejection_reason = None
        self.updated_at = datetime.utcnow()

    def reject(self, reason: str):
        """Reject listing."""
        if self.status != ListingStatus.PENDING_REVIEW:
            raise ValueError("Only pending listings can be rejected")

        self.status = ListingStatus.REJECTED
        self.rejection_reason = reason
        self.updated_at = datetime.utcnow()

    def suspend(self, reason: str):
        """Suspend published listing."""
        if self.status != ListingStatus.PUBLISHED:
            raise ValueError("Only published listings can be suspended")

        self.status = ListingStatus.SUSPENDED
        self.rejection_reason = reason
        self.updated_at = datetime.utcnow()

    def archive(self):
        """Archive listing."""
        self.status = ListingStatus.ARCHIVED
        self.updated_at = datetime.utcnow()

    def record_view(self):
        """Record a view."""
        self.stats = self.stats.with_view()

    def record_download(self):
        """Record a download."""
        self.stats = self.stats.with_download()

    def set_featured(self, featured: bool):
        """Set featured status."""
        self.is_featured = featured
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.listing_id,  # Frontend expects 'id'
            "listing_id": self.listing_id,  # Keep for backwards compatibility
            "seller_id": self.seller_id,
            "resource_type": self.resource_type.value,
            "resource_type_display": self.resource_type.display_name,
            "category": self.category.value,
            "category_display": self.category.display_name,
            "source": self.source.value,
            "source_display": self.source.display_name,
            "title": self.metadata.title,
            "description": self.metadata.description,
            "tags": self.metadata.tags,
            "preview_url": self.metadata.preview_url,
            "thumbnail_url": self.metadata.thumbnail_url,
            "price_type": self.price_type.value,
            "credit_price": self.credit_price,
            "is_free": self.is_free,
            "allowed_tiers": self.allowed_tiers,
            "status": self.status.value,
            "is_featured": self.is_featured,
            "stats": self.stats.to_dict(),
            "created_at": self.created_at.isoformat(),
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }
