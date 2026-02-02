"""
Supabase Static Page Repository Implementation

Implements StaticPageRepository interface using Supabase AsyncClient.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Any
from uuid import UUID

from supabase._async.client import AsyncClient

from domains.static_pages.entities import StaticPage, StaticPageSummary, StaticPageType
from domains.static_pages.repository import StaticPageRepository

logger = logging.getLogger(__name__)


class SupabaseStaticPageRepository(StaticPageRepository):
    """
    Supabase implementation of StaticPageRepository.

    Uses AsyncClient for async database operations.
    """

    def __init__(self, client: AsyncClient):
        self._client = client

    # ==========================================
    # Public Read Operations
    # ==========================================

    async def get_by_slug(self, slug: str) -> Optional[StaticPage]:
        """Get a published static page by slug."""
        try:
            result = await self._client.table('static_pages').select('*').eq(
                'slug', slug
            ).eq('is_published', True).limit(1).execute()

            if result is None or not result.data:
                return None

            return self._to_static_page(result.data[0])

        except Exception as e:
            logger.error(f"[SupabaseStaticPageRepository] Error getting static page by slug: {e}")
            raise

    async def list_published(
        self,
        page_type: Optional[StaticPageType] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[StaticPageSummary]:
        """List published static pages."""
        try:
            query = self._client.table('static_pages').select(
                'id, slug, title, subtitle, page_type, icon, is_published, '
                'last_updated_display, sort_order, created_at, updated_at'
            ).eq('is_published', True)

            if page_type:
                query = query.eq('page_type', page_type.value)

            query = query.order('sort_order', desc=False).order('title', desc=False)
            query = query.range(offset, offset + limit - 1)

            result = await query.execute()
            return [self._to_static_page_summary(row) for row in result.data]

        except Exception as e:
            logger.error(f"[SupabaseStaticPageRepository] Error listing published static pages: {e}")
            raise

    async def count_published(
        self,
        page_type: Optional[StaticPageType] = None,
    ) -> int:
        """Count published static pages."""
        try:
            query = self._client.table('static_pages').select(
                'id', count='exact'
            ).eq('is_published', True)

            if page_type:
                query = query.eq('page_type', page_type.value)

            result = await query.execute()
            return result.count or 0

        except Exception as e:
            logger.error(f"[SupabaseStaticPageRepository] Error counting published static pages: {e}")
            raise

    # ==========================================
    # Admin Read Operations
    # ==========================================

    async def get_by_id(self, page_id: UUID) -> Optional[StaticPage]:
        """Get a static page by ID (including drafts)."""
        try:
            result = await self._client.table('static_pages').select('*').eq(
                'id', str(page_id)
            ).limit(1).execute()

            if result is None or not result.data:
                return None

            return self._to_static_page(result.data[0])

        except Exception as e:
            logger.error(f"[SupabaseStaticPageRepository] Error getting static page by id: {e}")
            raise

    async def list_all(
        self,
        page_type: Optional[StaticPageType] = None,
        include_drafts: bool = True,
        offset: int = 0,
        limit: int = 50,
    ) -> list[StaticPageSummary]:
        """List all static pages for admin."""
        try:
            query = self._client.table('static_pages').select(
                'id, slug, title, subtitle, page_type, icon, is_published, '
                'last_updated_display, sort_order, created_at, updated_at'
            )

            if not include_drafts:
                query = query.eq('is_published', True)

            if page_type:
                query = query.eq('page_type', page_type.value)

            query = query.order('sort_order', desc=False).order('title', desc=False)
            query = query.range(offset, offset + limit - 1)

            result = await query.execute()
            return [self._to_static_page_summary(row) for row in result.data]

        except Exception as e:
            logger.error(f"[SupabaseStaticPageRepository] Error listing all static pages: {e}")
            raise

    async def count_all(
        self,
        page_type: Optional[StaticPageType] = None,
        published_only: bool = False,
    ) -> int:
        """Count all static pages for admin."""
        try:
            query = self._client.table('static_pages').select('id', count='exact')

            if published_only:
                query = query.eq('is_published', True)

            if page_type:
                query = query.eq('page_type', page_type.value)

            result = await query.execute()
            return result.count or 0

        except Exception as e:
            logger.error(f"[SupabaseStaticPageRepository] Error counting all static pages: {e}")
            raise

    # ==========================================
    # Admin Write Operations
    # ==========================================

    async def create(self, page: StaticPage) -> StaticPage:
        """Create a new static page."""
        try:
            data = self._to_dict(page)
            result = await self._client.table('static_pages').insert(data).execute()

            if not result.data:
                raise Exception("Failed to create static page")

            return self._to_static_page(result.data[0])

        except Exception as e:
            logger.error(f"[SupabaseStaticPageRepository] Error creating static page: {e}")
            raise

    async def update(self, page: StaticPage) -> StaticPage:
        """Update an existing static page."""
        try:
            data = self._to_dict(page)
            # Remove id from update data
            page_id = data.pop('id')

            result = await self._client.table('static_pages').update(data).eq(
                'id', page_id
            ).execute()

            if not result.data:
                raise Exception("Failed to update static page")

            return self._to_static_page(result.data[0])

        except Exception as e:
            logger.error(f"[SupabaseStaticPageRepository] Error updating static page: {e}")
            raise

    async def delete(self, page_id: UUID) -> bool:
        """Delete a static page."""
        try:
            result = await self._client.table('static_pages').delete().eq(
                'id', str(page_id)
            ).execute()

            return len(result.data) > 0

        except Exception as e:
            logger.error(f"[SupabaseStaticPageRepository] Error deleting static page: {e}")
            raise

    async def publish(self, page_id: UUID) -> Optional[StaticPage]:
        """Publish a static page."""
        try:
            result = await self._client.table('static_pages').update({
                'is_published': True,
                'published_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }).eq('id', str(page_id)).execute()

            if not result.data:
                return None

            return self._to_static_page(result.data[0])

        except Exception as e:
            logger.error(f"[SupabaseStaticPageRepository] Error publishing static page: {e}")
            raise

    async def unpublish(self, page_id: UUID) -> Optional[StaticPage]:
        """Unpublish a static page (revert to draft)."""
        try:
            result = await self._client.table('static_pages').update({
                'is_published': False,
                'published_at': None,
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }).eq('id', str(page_id)).execute()

            if not result.data:
                return None

            return self._to_static_page(result.data[0])

        except Exception as e:
            logger.error(f"[SupabaseStaticPageRepository] Error unpublishing static page: {e}")
            raise

    # ==========================================
    # Utility Operations
    # ==========================================

    async def slug_exists(self, slug: str, exclude_id: Optional[UUID] = None) -> bool:
        """Check if a slug already exists."""
        try:
            query = self._client.table('static_pages').select('id').eq('slug', slug)

            if exclude_id:
                query = query.neq('id', str(exclude_id))

            result = await query.execute()
            return len(result.data) > 0

        except Exception as e:
            logger.error(f"[SupabaseStaticPageRepository] Error checking slug: {e}")
            raise

    # ==========================================
    # Mapping Methods
    # ==========================================

    def _to_static_page(self, data: dict[str, Any]) -> StaticPage:
        """Convert database row to StaticPage entity."""
        return StaticPage(
            id=UUID(data['id']),
            slug=data['slug'],
            title=data['title'],
            content=data['content'],
            page_type=StaticPageType(data['page_type']),
            subtitle=data.get('subtitle'),
            icon=data.get('icon'),
            hero_gradient=data.get('hero_gradient'),
            meta_title=data.get('meta_title'),
            meta_description=data.get('meta_description'),
            schema_data=data.get('schema_data'),
            extra_data=data.get('extra_data') or {},
            is_published=data.get('is_published', False),
            published_at=self._parse_datetime(data.get('published_at')),
            last_updated_display=data.get('last_updated_display'),
            sort_order=data.get('sort_order', 0),
            created_at=self._parse_datetime(data.get('created_at')),
            updated_at=self._parse_datetime(data.get('updated_at')),
        )

    def _to_static_page_summary(self, data: dict[str, Any]) -> StaticPageSummary:
        """Convert database row to StaticPageSummary entity."""
        return StaticPageSummary(
            id=UUID(data['id']),
            slug=data['slug'],
            title=data['title'],
            page_type=StaticPageType(data['page_type']),
            subtitle=data.get('subtitle'),
            icon=data.get('icon'),
            is_published=data.get('is_published', False),
            last_updated_display=data.get('last_updated_display'),
            sort_order=data.get('sort_order', 0),
            created_at=self._parse_datetime(data.get('created_at')),
            updated_at=self._parse_datetime(data.get('updated_at')),
        )

    def _to_dict(self, page: StaticPage) -> dict[str, Any]:
        """Convert StaticPage entity to database dict."""
        return {
            'id': str(page.id),
            'slug': page.slug,
            'title': page.title,
            'content': page.content,
            'page_type': page.page_type.value,
            'subtitle': page.subtitle,
            'icon': page.icon,
            'hero_gradient': page.hero_gradient,
            'meta_title': page.meta_title,
            'meta_description': page.meta_description,
            'schema_data': page.schema_data,
            'extra_data': page.extra_data,
            'is_published': page.is_published,
            'published_at': page.published_at.isoformat() if page.published_at else None,
            'last_updated_display': page.last_updated_display,
            'sort_order': page.sort_order,
            'created_at': page.created_at.isoformat() if page.created_at else None,
            'updated_at': page.updated_at.isoformat() if page.updated_at else None,
        }

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        """Parse datetime from string."""
        if not value:
            return None
        try:
            # Handle ISO format with timezone
            if value.endswith('Z'):
                value = value[:-1] + '+00:00'
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None
