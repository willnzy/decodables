"""
Article Domain Entities.

@module domains.articles.entities
@version 1.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Union
from uuid import UUID


def _parse_datetime(value: Union[str, datetime, None]) -> Optional[datetime]:
    """Parse datetime from string or return as-is if already datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        # Handle ISO format with timezone (e.g., "2026-01-12T20:55:43.192958+00:00")
        try:
            # Remove 'Z' suffix if present and handle timezone
            if value.endswith('Z'):
                value = value[:-1] + '+00:00'
            return datetime.fromisoformat(value)
        except ValueError:
            # Fallback: try without timezone
            try:
                return datetime.fromisoformat(value.replace('+00:00', '').replace('+00', ''))
            except ValueError:
                return None
    return None


class ArticleCategory(str, Enum):
    """Article category enumeration."""
    MANUAL = "manual"               # Help documentation, tutorials
    NEWS = "news"                   # Announcements, updates
    CHANGELOG = "changelog"         # Release notes
    FAQ = "faq"                     # Frequently asked questions
    TROUBLESHOOTING = "troubleshooting"  # Common issues & solutions


@dataclass
class Article:
    """
    Article domain entity.

    Represents a piece of content that can be displayed on the website.
    """
    id: UUID
    slug: str
    title: str
    content: str  # Markdown content
    category: ArticleCategory

    # Optional fields
    summary: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    cover_image: Optional[str] = None

    # Publishing state
    is_published: bool = False
    published_at: Optional[datetime] = None

    # Metadata
    author_id: Optional[str] = None
    sort_order: int = 0
    view_count: int = 0

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Soft delete (match campaigns/daily_themes/holidays pattern)
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    recovery_expires_at: Optional[datetime] = None

    def publish(self) -> None:
        """Mark article as published."""
        self.is_published = True
        self.published_at = datetime.now(timezone.utc)

    def unpublish(self) -> None:
        """Mark article as unpublished (draft)."""
        self.is_published = False
        self.published_at = None

    def increment_view_count(self) -> None:
        """Increment the view count."""
        self.view_count += 1

    @classmethod
    def from_dict(cls, data: dict) -> "Article":
        """Create Article from dictionary."""
        # Handle category conversion
        category = data.get("category")
        if isinstance(category, str):
            category = ArticleCategory(category)

        # Handle tags - ensure it's a list
        tags = data.get("tags", [])
        if isinstance(tags, str):
            import json
            try:
                tags = json.loads(tags)
            except (json.JSONDecodeError, TypeError, ValueError):
                tags = []

        return cls(
            id=UUID(data["id"]) if isinstance(data.get("id"), str) else data.get("id"),
            slug=data.get("slug", ""),
            title=data.get("title", ""),
            content=data.get("content", ""),
            category=category,
            summary=data.get("summary"),
            tags=tags if isinstance(tags, list) else [],
            cover_image=data.get("cover_image"),
            is_published=data.get("is_published", False),
            published_at=_parse_datetime(data.get("published_at")),
            author_id=data.get("author_id"),
            sort_order=data.get("sort_order", 0),
            view_count=data.get("view_count", 0),
            created_at=_parse_datetime(data.get("created_at")),
            updated_at=_parse_datetime(data.get("updated_at")),
            is_deleted=data.get("is_deleted", False),
            deleted_at=_parse_datetime(data.get("deleted_at")),
            recovery_expires_at=_parse_datetime(data.get("recovery_expires_at")),
        )

    def to_dict(self) -> dict:
        """Convert Article to dictionary."""
        return {
            "id": str(self.id),
            "slug": self.slug,
            "title": self.title,
            "content": self.content,
            "category": self.category.value if isinstance(self.category, ArticleCategory) else self.category,
            "summary": self.summary,
            "tags": self.tags,
            "cover_image": self.cover_image,
            "is_published": self.is_published,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "author_id": self.author_id,
            "sort_order": self.sort_order,
            "view_count": self.view_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "recovery_expires_at": self.recovery_expires_at.isoformat() if self.recovery_expires_at else None,
        }


@dataclass
class ArticleSummary:
    """
    Lightweight article representation for listings.

    Used in list views to avoid loading full content.
    """
    id: UUID
    slug: str
    title: str
    summary: Optional[str]
    category: ArticleCategory
    tags: List[str]
    cover_image: Optional[str]
    is_featured: bool
    is_published: bool
    published_at: Optional[datetime]
    view_count: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    @classmethod
    def from_dict(cls, data: dict) -> "ArticleSummary":
        """Create ArticleSummary from dictionary."""
        category = data.get("category")
        if isinstance(category, str):
            category = ArticleCategory(category)

        tags = data.get("tags", [])
        if isinstance(tags, str):
            import json
            try:
                tags = json.loads(tags)
            except (json.JSONDecodeError, TypeError, ValueError):
                tags = []

        return cls(
            id=UUID(data["id"]) if isinstance(data.get("id"), str) else data.get("id"),
            slug=data.get("slug", ""),
            title=data.get("title", ""),
            summary=data.get("summary"),
            category=category,
            tags=tags if isinstance(tags, list) else [],
            cover_image=data.get("cover_image"),
            is_featured=data.get("is_featured", False),
            is_published=data.get("is_published", False),
            published_at=_parse_datetime(data.get("published_at")),
            view_count=data.get("view_count", 0),
            created_at=_parse_datetime(data.get("created_at")),
            updated_at=_parse_datetime(data.get("updated_at")),
        )

    def to_dict(self) -> dict:
        """Convert ArticleSummary to dictionary."""
        return {
            "id": str(self.id),
            "slug": self.slug,
            "title": self.title,
            "summary": self.summary,
            "category": self.category.value if isinstance(self.category, ArticleCategory) else self.category,
            "tags": self.tags,
            "cover_image": self.cover_image,
            "is_featured": self.is_featured,
            "is_published": self.is_published,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "view_count": self.view_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
