"""
Supabase Article Repository Implementation.

@module infrastructure.repositories.article_repository
@version 2.0.0 (AsyncClient migration)

Changes in v2.0:
- Migrated all methods to use AsyncClient with await
- All .execute() calls now properly awaited
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from core.utils.validation import sanitize_postgrest_query
from domains.articles.entities import Article, ArticleSummary, ArticleCategory
from domains.articles.repository import ArticleRepository

logger = logging.getLogger(__name__)


class SupabaseArticleRepository(ArticleRepository):
    """
    Supabase-based implementation of ArticleRepository.
    """

    def __init__(self, db_client):
        """
        Initialize with Supabase client.

        Args:
            db_client: Supabase client instance
        """
        self.db = db_client
        self.table = "articles"

    @staticmethod
    def _escape_or_filter_query(query: str) -> str:
        """Escape chars that manipulate PostgREST .or_() filter structure.

        Strips structural characters (comma, dot, parens) that could be used
        to inject additional filter conditions, then applies ILIKE wildcard
        escaping via sanitize_postgrest_query.
        """
        for char in (',', '.', '(', ')'):
            query = query.replace(char, '')
        return sanitize_postgrest_query(query.strip())

    @staticmethod
    def _is_not_found_error(error: Exception) -> bool:
        """Check if error is a PostgREST PGRST116 (0 rows for .single())."""
        code = getattr(error, 'code', None)
        if code == 'PGRST116':
            return True
        return 'pgrst116' in str(error).lower()

    # ==========================================
    # Read Operations
    # ==========================================

    async def get_by_id(self, article_id: UUID) -> Optional[Article]:
        """Get article by ID."""
        try:
            response = await self.db.table(self.table).select("*").eq("id", str(article_id)).single().execute()
            if response.data:
                return Article.from_dict(response.data)
            return None
        except Exception as e:
            if self._is_not_found_error(e):
                logger.debug(f"[ArticleRepo] Article not found by ID: {article_id}")
                return None
            logger.error(f"[ArticleRepo] Error getting article by ID: {e}")
            return None

    async def get_by_slug(self, slug: str) -> Optional[Article]:
        """Get published article by slug (public-facing, excludes soft-deleted)."""
        try:
            response = await self.db.table(self.table).select("*").eq("slug", slug).eq("is_deleted", False).single().execute()
            if response.data:
                return Article.from_dict(response.data)
            return None
        except Exception as e:
            if self._is_not_found_error(e):
                logger.debug(f"[ArticleRepo] Article not found by slug: {slug}")
                return None
            logger.error(f"[ArticleRepo] Error getting article by slug: {e}")
            return None

    async def list_published(
        self,
        category: Optional[ArticleCategory] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> List[ArticleSummary]:
        """List published articles (excludes soft-deleted)."""
        try:
            # Select only fields needed for summary (exclude content for performance)
            query = self.db.table(self.table).select(
                "id, slug, title, summary, category, tags, cover_image, is_featured, "
                "is_published, published_at, view_count, created_at, updated_at"
            ).eq("is_published", True).eq("is_deleted", False).order("published_at", desc=True)

            if category:
                query = query.eq("category", category.value)

            response = await query.range(offset, offset + limit - 1).execute()

            return [ArticleSummary.from_dict(item) for item in response.data or []]
        except Exception as e:
            logger.error(f"[ArticleRepo] Error listing published articles: {e}")
            return []

    async def list_all(
        self,
        category: Optional[ArticleCategory] = None,
        include_drafts: bool = True,
        offset: int = 0,
        limit: int = 20,
    ) -> List[ArticleSummary]:
        """List all articles (for admin — includes soft-deleted)."""
        try:
            query = self.db.table(self.table).select(
                "id, slug, title, summary, category, tags, cover_image, is_featured, "
                "is_published, published_at, view_count, created_at, updated_at"
            ).order("updated_at", desc=True)

            if not include_drafts:
                query = query.eq("is_published", True)

            if category:
                query = query.eq("category", category.value)

            response = await query.range(offset, offset + limit - 1).execute()

            return [ArticleSummary.from_dict(item) for item in response.data or []]
        except Exception as e:
            logger.error(f"[ArticleRepo] Error listing all articles: {e}")
            return []

    async def count(
        self,
        category: Optional[ArticleCategory] = None,
        published_only: bool = False,
    ) -> int:
        """Count articles."""
        try:
            query = self.db.table(self.table).select("id", count="exact")

            if published_only:
                query = query.eq("is_published", True).eq("is_deleted", False)

            if category:
                query = query.eq("category", category.value)

            response = await query.execute()
            return response.count or 0
        except Exception as e:
            logger.error(f"[ArticleRepo] Error counting articles: {e}")
            return 0

    async def get_categories_with_counts(self) -> List[dict]:
        """Get all categories with published article counts via RPC (single query)."""
        try:
            response = await self.db.rpc("get_article_category_counts").execute()
            results = []
            # Build results from RPC response, ensuring all categories are represented
            rpc_data = {row["category"]: row["published_count"] for row in (response.data or [])}
            for cat in ArticleCategory:
                results.append({
                    "category": cat.value,
                    "published_count": rpc_data.get(cat.value, 0),
                })
            return results
        except Exception as e:
            logger.error(f"[ArticleRepo] Error getting categories: {e}")
            return []

    async def list_featured(
        self,
        category: Optional[ArticleCategory] = None,
        limit: int = 4,
    ) -> List[ArticleSummary]:
        """List featured published articles (excludes soft-deleted)."""
        try:
            query = self.db.table(self.table).select(
                "id, slug, title, summary, category, tags, cover_image, is_featured, "
                "is_published, published_at, view_count, created_at, updated_at"
            ).eq("is_published", True).eq("is_featured", True).eq("is_deleted", False).order("published_at", desc=True)

            if category:
                query = query.eq("category", category.value)

            response = await query.limit(limit).execute()

            return [ArticleSummary.from_dict(item) for item in response.data or []]
        except Exception as e:
            logger.error(f"[ArticleRepo] Error listing featured articles: {e}")
            return []

    # ==========================================
    # Write Operations
    # ==========================================

    async def create(self, article: Article) -> Article:
        """Create a new article."""
        try:
            data = {
                "id": str(article.id),
                "slug": article.slug,
                "title": article.title,
                "content": article.content,
                "category": article.category.value if isinstance(article.category, ArticleCategory) else article.category,
                "summary": article.summary,
                "tags": article.tags,
                "cover_image": article.cover_image,
                "is_published": article.is_published,
                "published_at": article.published_at.isoformat() if article.published_at else None,
                "author_id": article.author_id,
                "sort_order": article.sort_order,
                "view_count": article.view_count,
                "created_at": article.created_at.isoformat() if article.created_at else None,
                "updated_at": article.updated_at.isoformat() if article.updated_at else None,
            }

            response = await self.db.table(self.table).insert(data).execute()

            if response.data:
                return Article.from_dict(response.data[0])
            return article
        except Exception as e:
            logger.error(f"[ArticleRepo] Error creating article: {e}")
            raise

    async def update(self, article: Article) -> Article:
        """Update an existing article."""
        try:
            data = {
                "slug": article.slug,
                "title": article.title,
                "content": article.content,
                "category": article.category.value if isinstance(article.category, ArticleCategory) else article.category,
                "summary": article.summary,
                "tags": article.tags,
                "cover_image": article.cover_image,
                "is_published": article.is_published,
                "published_at": article.published_at.isoformat() if article.published_at else None,
                "sort_order": article.sort_order,
                "updated_at": article.updated_at.isoformat() if article.updated_at else None,
            }

            response = await self.db.table(self.table).update(data).eq("id", str(article.id)).execute()

            if response.data:
                return Article.from_dict(response.data[0])
            return article
        except Exception as e:
            logger.error(f"[ArticleRepo] Error updating article: {e}")
            raise

    async def delete(self, article_id: UUID) -> bool:
        """Soft delete an article (sets is_deleted=true, deleted_at=current time)."""
        try:
            response = await self.db.table(self.table).update({
                "is_deleted": True,
                "deleted_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", str(article_id)).execute()
            return len(response.data or []) > 0
        except Exception as e:
            logger.error(f"[ArticleRepo] Error soft-deleting article: {e}")
            return False

    async def hard_delete(self, article_id: UUID) -> bool:
        """Permanently delete an article (for data cleanup only)."""
        try:
            response = await self.db.table(self.table).delete().eq("id", str(article_id)).execute()
            return len(response.data or []) > 0
        except Exception as e:
            logger.error(f"[ArticleRepo] Error hard-deleting article: {e}")
            return False

    async def increment_view_count(self, article_id: UUID) -> bool:
        """Increment article view count atomically via RPC."""
        try:
            await self.db.rpc("increment_article_view_count", {
                "p_article_id": str(article_id),
            }).execute()
            return True
        except Exception as e:
            logger.error(f"[ArticleRepo] Error incrementing view count: {e}")
            return False

    # ==========================================
    # Search Operations
    # ==========================================

    async def search(
        self,
        query: str,
        category: Optional[ArticleCategory] = None,
        published_only: bool = True,
        offset: int = 0,
        limit: int = 20,
    ) -> List[ArticleSummary]:
        """Search articles by title and content."""
        try:
            # Escape structural + ILIKE wildcard chars to prevent filter injection
            sanitized = self._escape_or_filter_query(query)
            search_pattern = f"%{sanitized}%"

            db_query = self.db.table(self.table).select(
                "id, slug, title, summary, category, tags, cover_image, is_featured, "
                "is_published, published_at, view_count, created_at, updated_at"
            ).or_(f"title.ilike.{search_pattern},content.ilike.{search_pattern},summary.ilike.{search_pattern}")

            if published_only:
                db_query = db_query.eq("is_published", True).eq("is_deleted", False)

            if category:
                db_query = db_query.eq("category", category.value)

            response = await db_query.order("published_at", desc=True).range(offset, offset + limit - 1).execute()

            return [ArticleSummary.from_dict(item) for item in response.data or []]
        except Exception as e:
            logger.error(f"[ArticleRepo] Error searching articles: {e}")
            return []

    async def slug_exists(self, slug: str, exclude_id: Optional[UUID] = None) -> bool:
        """Check if a slug already exists (excludes soft-deleted to allow slug reuse)."""
        try:
            query = self.db.table(self.table).select("id").eq("slug", slug).eq("is_deleted", False)

            if exclude_id:
                query = query.neq("id", str(exclude_id))

            response = await query.execute()
            return len(response.data or []) > 0
        except Exception as e:
            logger.error(f"[ArticleRepo] Error checking slug existence: {e}")
            return False
