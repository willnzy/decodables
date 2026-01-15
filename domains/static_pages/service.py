"""
Static Pages Domain Service

Business logic for static page management.
"""

import logging
import re
from datetime import datetime
from typing import Optional, Any
from uuid import UUID, uuid4

from .entities import StaticPage, StaticPageSummary, StaticPageType
from .repository import StaticPageRepository

logger = logging.getLogger(__name__)


class StaticPageService:
    """
    Static page management service.

    Handles business logic for static pages CMS.
    """

    def __init__(self, repository: StaticPageRepository):
        self._repository = repository

    # ==========================================
    # Public Operations
    # ==========================================

    async def get_static_page(self, slug: str) -> Optional[StaticPage]:
        """
        Get a published static page by slug.

        Args:
            slug: Page URL identifier

        Returns:
            StaticPage if found and published, None otherwise
        """
        logger.info(f"[StaticPageService] Getting static page: {slug}")
        page = await self._repository.get_by_slug(slug)

        if not page:
            logger.warning(f"[StaticPageService] Static page not found: {slug}")
            return None

        return page

    async def list_static_pages(
        self,
        page_type: Optional[StaticPageType] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[StaticPageSummary]:
        """
        List published static pages.

        Args:
            page_type: Filter by page type
            offset: Pagination offset
            limit: Maximum results

        Returns:
            List of StaticPageSummary objects
        """
        logger.info(f"[StaticPageService] Listing static pages: type={page_type}, offset={offset}, limit={limit}")
        return await self._repository.list_published(
            page_type=page_type,
            offset=offset,
            limit=limit,
        )

    async def get_static_page_count(
        self,
        page_type: Optional[StaticPageType] = None,
    ) -> int:
        """
        Count published static pages.

        Args:
            page_type: Filter by page type

        Returns:
            Number of published static pages
        """
        return await self._repository.count_published(page_type=page_type)

    # ==========================================
    # Admin Operations
    # ==========================================

    async def admin_get_static_page(self, page_id: UUID) -> Optional[StaticPage]:
        """
        Get a static page by ID (admin, includes drafts).

        Args:
            page_id: Page UUID

        Returns:
            StaticPage if found, None otherwise
        """
        logger.info(f"[StaticPageService] Admin getting static page: {page_id}")
        return await self._repository.get_by_id(page_id)

    async def admin_list_static_pages(
        self,
        page_type: Optional[StaticPageType] = None,
        include_drafts: bool = True,
        offset: int = 0,
        limit: int = 50,
    ) -> list[StaticPageSummary]:
        """
        List all static pages (admin).

        Args:
            page_type: Filter by page type
            include_drafts: Include unpublished pages
            offset: Pagination offset
            limit: Maximum results

        Returns:
            List of StaticPageSummary objects
        """
        logger.info(f"[StaticPageService] Admin listing static pages: type={page_type}, drafts={include_drafts}")
        return await self._repository.list_all(
            page_type=page_type,
            include_drafts=include_drafts,
            offset=offset,
            limit=limit,
        )

    async def admin_get_count(
        self,
        page_type: Optional[StaticPageType] = None,
        published_only: bool = False,
    ) -> int:
        """
        Count static pages (admin).

        Args:
            page_type: Filter by page type
            published_only: Only count published pages

        Returns:
            Number of static pages
        """
        return await self._repository.count_all(
            page_type=page_type,
            published_only=published_only,
        )

    async def create_static_page(
        self,
        slug: str,
        title: str,
        content: str,
        page_type: StaticPageType,
        subtitle: Optional[str] = None,
        icon: Optional[str] = None,
        hero_gradient: Optional[str] = None,
        meta_title: Optional[str] = None,
        meta_description: Optional[str] = None,
        schema_data: Optional[dict[str, Any]] = None,
        extra_data: Optional[dict[str, Any]] = None,
        last_updated_display: Optional[str] = None,
        sort_order: int = 0,
    ) -> StaticPage:
        """
        Create a new static page.

        Args:
            slug: URL identifier (will be normalized)
            title: Page title
            content: Markdown content
            page_type: Page type
            subtitle: Optional subtitle
            icon: Lucide icon name
            hero_gradient: CSS gradient classes
            meta_title: SEO title
            meta_description: SEO description
            schema_data: JSON-LD schema
            extra_data: Additional structured data
            last_updated_display: Display date string
            sort_order: Sort weight

        Returns:
            Created StaticPage

        Raises:
            ValueError: If slug already exists
        """
        logger.info(f"[StaticPageService] Creating static page: {slug}")

        # Normalize slug
        normalized_slug = self._normalize_slug(slug)

        # Check slug uniqueness
        if await self._repository.slug_exists(normalized_slug):
            raise ValueError(f"Slug already exists: {normalized_slug}")

        # Create page entity
        page = StaticPage(
            id=uuid4(),
            slug=normalized_slug,
            title=title,
            content=content,
            page_type=page_type,
            subtitle=subtitle,
            icon=icon,
            hero_gradient=hero_gradient,
            meta_title=meta_title,
            meta_description=meta_description,
            schema_data=schema_data,
            extra_data=extra_data or {},
            is_published=False,
            published_at=None,
            last_updated_display=last_updated_display,
            sort_order=sort_order,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        created = await self._repository.create(page)
        logger.info(f"[StaticPageService] Static page created: {created.id}")
        return created

    async def update_static_page(
        self,
        page_id: UUID,
        slug: Optional[str] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        page_type: Optional[StaticPageType] = None,
        subtitle: Optional[str] = None,
        icon: Optional[str] = None,
        hero_gradient: Optional[str] = None,
        meta_title: Optional[str] = None,
        meta_description: Optional[str] = None,
        schema_data: Optional[dict[str, Any]] = None,
        extra_data: Optional[dict[str, Any]] = None,
        last_updated_display: Optional[str] = None,
        sort_order: Optional[int] = None,
    ) -> Optional[StaticPage]:
        """
        Update an existing static page.

        Args:
            page_id: Page UUID
            slug: New slug (optional)
            title: New title (optional)
            content: New content (optional)
            page_type: New page type (optional)
            subtitle: New subtitle (optional)
            icon: New icon (optional)
            hero_gradient: New gradient (optional)
            meta_title: New SEO title (optional)
            meta_description: New SEO description (optional)
            schema_data: New schema data (optional)
            extra_data: New extra data (optional)
            last_updated_display: New display date (optional)
            sort_order: New sort order (optional)

        Returns:
            Updated StaticPage if found, None otherwise

        Raises:
            ValueError: If new slug already exists
        """
        logger.info(f"[StaticPageService] Updating static page: {page_id}")

        # Get existing page
        page = await self._repository.get_by_id(page_id)
        if not page:
            logger.warning(f"[StaticPageService] Static page not found: {page_id}")
            return None

        # Handle slug update
        if slug is not None:
            normalized_slug = self._normalize_slug(slug)
            if normalized_slug != page.slug:
                if await self._repository.slug_exists(normalized_slug, exclude_id=page_id):
                    raise ValueError(f"Slug already exists: {normalized_slug}")
                page.slug = normalized_slug

        # Update fields if provided
        if title is not None:
            page.title = title
        if content is not None:
            page.content = content
        if page_type is not None:
            page.page_type = page_type
        if subtitle is not None:
            page.subtitle = subtitle
        if icon is not None:
            page.icon = icon
        if hero_gradient is not None:
            page.hero_gradient = hero_gradient
        if meta_title is not None:
            page.meta_title = meta_title
        if meta_description is not None:
            page.meta_description = meta_description
        if schema_data is not None:
            page.schema_data = schema_data
        if extra_data is not None:
            page.extra_data = extra_data
        if last_updated_display is not None:
            page.last_updated_display = last_updated_display
        if sort_order is not None:
            page.sort_order = sort_order

        page.updated_at = datetime.utcnow()

        updated = await self._repository.update(page)
        logger.info(f"[StaticPageService] Static page updated: {page_id}")
        return updated

    async def publish_static_page(self, page_id: UUID) -> Optional[StaticPage]:
        """
        Publish a static page.

        Args:
            page_id: Page UUID

        Returns:
            Published StaticPage if found, None otherwise
        """
        logger.info(f"[StaticPageService] Publishing static page: {page_id}")
        page = await self._repository.publish(page_id)

        if page:
            logger.info(f"[StaticPageService] Static page published: {page_id}")
        else:
            logger.warning(f"[StaticPageService] Static page not found for publish: {page_id}")

        return page

    async def unpublish_static_page(self, page_id: UUID) -> Optional[StaticPage]:
        """
        Unpublish a static page (revert to draft).

        Args:
            page_id: Page UUID

        Returns:
            Unpublished StaticPage if found, None otherwise
        """
        logger.info(f"[StaticPageService] Unpublishing static page: {page_id}")
        page = await self._repository.unpublish(page_id)

        if page:
            logger.info(f"[StaticPageService] Static page unpublished: {page_id}")
        else:
            logger.warning(f"[StaticPageService] Static page not found for unpublish: {page_id}")

        return page

    async def delete_static_page(self, page_id: UUID) -> bool:
        """
        Delete a static page.

        Args:
            page_id: Page UUID

        Returns:
            True if deleted, False if not found
        """
        logger.info(f"[StaticPageService] Deleting static page: {page_id}")
        result = await self._repository.delete(page_id)

        if result:
            logger.info(f"[StaticPageService] Static page deleted: {page_id}")
        else:
            logger.warning(f"[StaticPageService] Static page not found for delete: {page_id}")

        return result

    # ==========================================
    # Utility Methods
    # ==========================================

    def _normalize_slug(self, slug: str) -> str:
        """
        Normalize slug to URL-safe format.

        Args:
            slug: Raw slug input

        Returns:
            Normalized slug (lowercase, hyphens only)
        """
        # Convert to lowercase
        normalized = slug.lower().strip()

        # Replace spaces and underscores with hyphens
        normalized = re.sub(r'[\s_]+', '-', normalized)

        # Remove non-alphanumeric characters except hyphens
        normalized = re.sub(r'[^a-z0-9-]', '', normalized)

        # Remove multiple consecutive hyphens
        normalized = re.sub(r'-+', '-', normalized)

        # Remove leading/trailing hyphens
        normalized = normalized.strip('-')

        return normalized
