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
    AssetCategory,
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
    """
    listing_id: str
    seller_id: str
    category: AssetCategory
    metadata: ListingMetadata
    price_type: PriceType = PriceType.FREE
    credit_price: int = 0
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
        category: AssetCategory,
        title: str,
        description: Optional[str] = None,
        price_type: PriceType = PriceType.FREE,
        credit_price: int = 0
    ) -> "Listing":
        """
        Factory method to create a new listing.

        Args:
            seller_id: User ID of seller
            category: Asset category
            title: Listing title
            description: Optional description
            price_type: Pricing model
            credit_price: Price in credits (if applicable)

        Returns:
            New Listing instance
        """
        listing_id = ListingId.generate()

        return cls(
            listing_id=str(listing_id),
            seller_id=seller_id,
            category=category,
            metadata=ListingMetadata(title=title, description=description),
            price_type=price_type,
            credit_price=credit_price if price_type == PriceType.CREDITS else 0,
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

    def can_access(self, user_id: str, user_tier: str = "free") -> bool:
        """
        Check if user can access this listing.

        Args:
            user_id: User ID
            user_tier: User's subscription tier

        Returns:
            True if user can access
        """
        if self.seller_id == user_id:
            return True
        if not self.is_published:
            return False
        if self.is_free:
            return True
        if self.requires_premium and user_tier in ("starter", "pro"):
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
        self.updated_at = datetime.utcnow()

    def set_pricing(self, price_type: PriceType, credit_price: int = 0):
        """
        Set listing pricing.

        Args:
            price_type: Pricing model
            credit_price: Price in credits
        """
        if not self.is_editable:
            raise ValueError("Cannot edit published listing")

        self.price_type = price_type
        self.credit_price = credit_price if price_type == PriceType.CREDITS else 0
        self.updated_at = datetime.utcnow()

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
            "listing_id": self.listing_id,
            "seller_id": self.seller_id,
            "category": self.category.value,
            "category_display": self.category.display_name,
            "title": self.metadata.title,
            "description": self.metadata.description,
            "tags": self.metadata.tags,
            "preview_url": self.metadata.preview_url,
            "thumbnail_url": self.metadata.thumbnail_url,
            "price_type": self.price_type.value,
            "credit_price": self.credit_price,
            "is_free": self.is_free,
            "status": self.status.value,
            "is_featured": self.is_featured,
            "stats": self.stats.to_dict(),
            "created_at": self.created_at.isoformat(),
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }
