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


class ResourceType(str, Enum):
    """
    Resource type - top-level classification.

    Distinguishes between single assets and project templates.
    """
    ASSET = "asset"      # Single asset (sticker, clipart, background, etc.)
    PROJECT = "project"  # Project template (mini-book, worksheet, etc.)

    @property
    def display_name(self) -> str:
        """Human-readable type name."""
        return "Asset" if self == ResourceType.ASSET else "Project"


class AssetCategory(str, Enum):
    """
    Asset category types - second-level classification.

    Based on the category system from Asset-Category-System-Design.md.
    """
    # Graphics categories
    CLIPART = "clipart"
    ILLUSTRATION = "illustration"
    PHOTO = "photo"
    BACKGROUND = "background"
    STICKER = "sticker"
    ICON = "icon"
    PATTERN = "pattern"
    ELEMENT = "element"
    EMOJI = "emoji"
    FRAME = "frame"
    CHARACTER = "character"
    SCENE = "scene"
    # Text/Font categories
    FONT = "font"
    # Project categories (for resource_type=project)
    TEMPLATE = "template"
    MINI_BOOK = "mini_book"
    WORKSHEET = "worksheet"
    FLASHCARD = "flashcard"

    @property
    def display_name(self) -> str:
        """Human-readable category name."""
        names = {
            AssetCategory.CLIPART: "Clipart",
            AssetCategory.ILLUSTRATION: "Illustration",
            AssetCategory.PHOTO: "Photo",
            AssetCategory.BACKGROUND: "Background",
            AssetCategory.STICKER: "Sticker",
            AssetCategory.ICON: "Icon",
            AssetCategory.PATTERN: "Pattern",
            AssetCategory.ELEMENT: "Element",
            AssetCategory.EMOJI: "Emoji",
            AssetCategory.FRAME: "Frame",
            AssetCategory.CHARACTER: "Character",
            AssetCategory.SCENE: "Scene",
            AssetCategory.FONT: "Font",
            AssetCategory.TEMPLATE: "Template",
            AssetCategory.MINI_BOOK: "Mini Book",
            AssetCategory.WORKSHEET: "Worksheet",
            AssetCategory.FLASHCARD: "Flashcard",
        }
        return names.get(self, self.value.replace("_", " ").title())

    @property
    def is_project_category(self) -> bool:
        """Check if this category is for projects."""
        return self in (
            AssetCategory.TEMPLATE,
            AssetCategory.MINI_BOOK,
            AssetCategory.WORKSHEET,
            AssetCategory.FLASHCARD,
        )


class ListingSource(str, Enum):
    """
    Listing source - where the asset comes from.
    """
    SYSTEM = "system"      # Built-in system assets
    USER = "user"          # User-uploaded assets
    AI = "ai"              # AI-generated assets
    COMMUNITY = "community"  # Community-shared assets

    @property
    def display_name(self) -> str:
        """Human-readable source name."""
        names = {
            ListingSource.SYSTEM: "System",
            ListingSource.USER: "User Upload",
            ListingSource.AI: "AI Generated",
            ListingSource.COMMUNITY: "Community",
        }
        return names.get(self, self.value.title())


class PriceType(str, Enum):
    """Pricing model types."""
    FREE = "t1"
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
    FREE = "t1"
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
