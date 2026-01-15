"""
Static Pages Repository Interface

Defines the contract for static page data access.
"""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from .entities import StaticPage, StaticPageSummary, StaticPageType


class StaticPageRepository(ABC):
    """
    Abstract repository interface for static pages.

    Implementations:
    - SupabaseStaticPageRepository (infrastructure layer)
    """

    # ==========================================
    # Public Read Operations
    # ==========================================

    @abstractmethod
    async def get_by_slug(self, slug: str) -> Optional[StaticPage]:
        """
        Get a published static page by slug.

        Args:
            slug: Page URL identifier (e.g., 'billing-policy')

        Returns:
            StaticPage if found and published, None otherwise
        """
        pass

    @abstractmethod
    async def list_published(
        self,
        page_type: Optional[StaticPageType] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[StaticPageSummary]:
        """
        List published static pages.

        Args:
            page_type: Filter by page type (optional)
            offset: Pagination offset
            limit: Maximum results to return

        Returns:
            List of StaticPageSummary objects
        """
        pass

    @abstractmethod
    async def count_published(
        self,
        page_type: Optional[StaticPageType] = None,
    ) -> int:
        """
        Count published static pages.

        Args:
            page_type: Filter by page type (optional)

        Returns:
            Number of published static pages
        """
        pass

    # ==========================================
    # Admin Read Operations
    # ==========================================

    @abstractmethod
    async def get_by_id(self, page_id: UUID) -> Optional[StaticPage]:
        """
        Get a static page by ID (including drafts).

        Args:
            page_id: Page UUID

        Returns:
            StaticPage if found, None otherwise
        """
        pass

    @abstractmethod
    async def list_all(
        self,
        page_type: Optional[StaticPageType] = None,
        include_drafts: bool = True,
        offset: int = 0,
        limit: int = 50,
    ) -> list[StaticPageSummary]:
        """
        List all static pages for admin.

        Args:
            page_type: Filter by page type (optional)
            include_drafts: Include unpublished pages
            offset: Pagination offset
            limit: Maximum results to return

        Returns:
            List of StaticPageSummary objects
        """
        pass

    @abstractmethod
    async def count_all(
        self,
        page_type: Optional[StaticPageType] = None,
        published_only: bool = False,
    ) -> int:
        """
        Count all static pages for admin.

        Args:
            page_type: Filter by page type (optional)
            published_only: Only count published pages

        Returns:
            Number of static pages
        """
        pass

    # ==========================================
    # Admin Write Operations
    # ==========================================

    @abstractmethod
    async def create(self, page: StaticPage) -> StaticPage:
        """
        Create a new static page.

        Args:
            page: StaticPage entity to create

        Returns:
            Created StaticPage with generated ID
        """
        pass

    @abstractmethod
    async def update(self, page: StaticPage) -> StaticPage:
        """
        Update an existing static page.

        Args:
            page: StaticPage entity with updated data

        Returns:
            Updated StaticPage
        """
        pass

    @abstractmethod
    async def delete(self, page_id: UUID) -> bool:
        """
        Delete a static page.

        Args:
            page_id: Page UUID to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def publish(self, page_id: UUID) -> Optional[StaticPage]:
        """
        Publish a static page.

        Args:
            page_id: Page UUID to publish

        Returns:
            Updated StaticPage if found, None otherwise
        """
        pass

    @abstractmethod
    async def unpublish(self, page_id: UUID) -> Optional[StaticPage]:
        """
        Unpublish a static page (revert to draft).

        Args:
            page_id: Page UUID to unpublish

        Returns:
            Updated StaticPage if found, None otherwise
        """
        pass

    # ==========================================
    # Utility Operations
    # ==========================================

    @abstractmethod
    async def slug_exists(self, slug: str, exclude_id: Optional[UUID] = None) -> bool:
        """
        Check if a slug already exists.

        Args:
            slug: Slug to check
            exclude_id: Exclude this page ID from check (for updates)

        Returns:
            True if slug exists, False otherwise
        """
        pass
