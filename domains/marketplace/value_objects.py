"""
Marketplace Value Objects - Immutable domain primitives.

@module domains.marketplace.value_objects
@version 1.0.0
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid


class ListingStatus(str, Enum):
    """Listing lifecycle status."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PUBLISHED = "published"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"

    @property
    def is_visible(self) -> bool:
        """Check if listing is publicly visible."""
        return self == ListingStatus.PUBLISHED

    @property
    def is_editable(self) -> bool:
        """Check if listing can be edited."""
        return self in (ListingStatus.DRAFT, ListingStatus.REJECTED)


class AssetCategory(str, Enum):
    """
    Asset category types.

    Based on the 10-category system from design docs.
    """
    CLIPART = "clipart"
    ILLUSTRATION = "illustration"
    PHOTO = "photo"
    BACKGROUND = "background"
    TEMPLATE = "template"
    FONT = "font"
    STICKER = "sticker"
    ICON = "icon"
    PATTERN = "pattern"
    ELEMENT = "element"

    @property
    def display_name(self) -> str:
        """Human-readable category name."""
        names = {
            AssetCategory.CLIPART: "Clipart",
            AssetCategory.ILLUSTRATION: "Illustration",
            AssetCategory.PHOTO: "Photo",
            AssetCategory.BACKGROUND: "Background",
            AssetCategory.TEMPLATE: "Template",
            AssetCategory.FONT: "Font",
            AssetCategory.STICKER: "Sticker",
            AssetCategory.ICON: "Icon",
            AssetCategory.PATTERN: "Pattern",
            AssetCategory.ELEMENT: "Element",
        }
        return names.get(self, self.value)


class PriceType(str, Enum):
    """Pricing model types."""
    FREE = "free"
    PREMIUM = "premium"  # Requires paid subscription
    CREDITS = "credits"  # Pay with credits


class ListingSortOrder(str, Enum):
    """Listing sort options."""
    LATEST = "latest"
    POPULAR = "popular"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    BEST_SELLING = "best_selling"


class PriceFilter(str, Enum):
    """Price filter options."""
    ALL = "all"
    FREE = "free"
    PAID = "paid"


@dataclass(frozen=True)
class ListingId:
    """
    Listing identifier value object.
    """
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("Listing ID cannot be empty")

    @classmethod
    def generate(cls) -> "ListingId":
        """Generate a new listing ID."""
        return cls(str(uuid.uuid4()))

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other) -> bool:
        if isinstance(other, ListingId):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return False

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass
class ListingMetadata:
    """
    Listing metadata value object.
    """
    title: str
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    preview_url: str = ""
    thumbnail_url: Optional[str] = None
    file_url: str = ""
    file_size: int = 0
    file_format: str = ""
    dimensions: Optional[str] = None  # e.g., "1080x1080"
    license_type: str = "standard"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "preview_url": self.preview_url,
            "thumbnail_url": self.thumbnail_url,
            "file_url": self.file_url,
            "file_size": self.file_size,
            "file_format": self.file_format,
            "dimensions": self.dimensions,
            "license_type": self.license_type,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ListingMetadata":
        """Create from dictionary."""
        return cls(
            title=data.get("title", "Untitled"),
            description=data.get("description"),
            tags=data.get("tags", []),
            preview_url=data.get("preview_url", ""),
            thumbnail_url=data.get("thumbnail_url"),
            file_url=data.get("file_url", ""),
            file_size=data.get("file_size", 0),
            file_format=data.get("file_format", ""),
            dimensions=data.get("dimensions"),
            license_type=data.get("license_type", "standard"),
        )


@dataclass(frozen=True)
class ListingStats:
    """
    Listing statistics value object.
    """
    view_count: int = 0
    download_count: int = 0
    like_count: int = 0
    purchase_count: int = 0
    rating_average: float = 0.0
    rating_count: int = 0

    def with_view(self) -> "ListingStats":
        """Return stats with incremented view count."""
        return ListingStats(
            view_count=self.view_count + 1,
            download_count=self.download_count,
            like_count=self.like_count,
            purchase_count=self.purchase_count,
            rating_average=self.rating_average,
            rating_count=self.rating_count,
        )

    def with_download(self) -> "ListingStats":
        """Return stats with incremented download count."""
        return ListingStats(
            view_count=self.view_count,
            download_count=self.download_count + 1,
            like_count=self.like_count,
            purchase_count=self.purchase_count,
            rating_average=self.rating_average,
            rating_count=self.rating_count,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "view_count": self.view_count,
            "download_count": self.download_count,
            "like_count": self.like_count,
            "purchase_count": self.purchase_count,
            "rating_average": self.rating_average,
            "rating_count": self.rating_count,
        }
