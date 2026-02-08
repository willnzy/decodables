"""
Static Pages Domain Entities

Defines StaticPage entity and related value objects.
Separate from project book pages (8 pages per mini-book).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any
from uuid import UUID


class StaticPageType(str, Enum):
    """Static page type enumeration."""
    LEGAL = "legal"           # billing-policy, term-of-service, privacy-policy
    COMPANY = "company"       # about-us
    GUIDE = "guide"           # marketplace-guidelines
    OTHER = "other"


@dataclass
class StaticPage:
    """
    Full StaticPage entity with all content.

    Used for:
    - Page detail view
    - Admin editing

    Note: This is for website static pages (legal, company info),
    NOT for project book pages (8 pages per mini-book).
    """
    id: UUID
    slug: str
    title: str
    content: str
    page_type: StaticPageType

    # Optional fields
    subtitle: Optional[str] = None
    icon: Optional[str] = None
    hero_gradient: Optional[str] = None

    # SEO
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    schema_data: Optional[dict[str, Any]] = None

    # Extra data (e.g., team members for about-us)
    extra_data: dict[str, Any] = field(default_factory=dict)

    # Status
    is_published: bool = False
    published_at: Optional[datetime] = None
    last_updated_display: Optional[str] = None

    # Sort
    sort_order: int = 0

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def get_effective_meta_title(self) -> str:
        """Get SEO title, falling back to page title."""
        return self.meta_title or f"{self.title} | Foliaz"

    def get_effective_meta_description(self) -> str:
        """Get SEO description, falling back to subtitle."""
        return self.meta_description or self.subtitle or ""


@dataclass
class StaticPageSummary:
    """
    Lightweight StaticPage summary for listings.

    Excludes content and extra_data for performance.
    """
    id: UUID
    slug: str
    title: str
    page_type: StaticPageType

    subtitle: Optional[str] = None
    icon: Optional[str] = None

    is_published: bool = False
    last_updated_display: Optional[str] = None
    sort_order: int = 0

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
