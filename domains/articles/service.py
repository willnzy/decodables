"""
Article Service - Business Logic Layer.

@module domains.articles.service
@version 1.0.0

Handles article management business logic.
"""

import logging
import re
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from .entities import Article, ArticleSummary, ArticleCategory
from .repository import ArticleRepository

logger = logging.getLogger(__name__)


class ArticleService:
    """
    Article service handling business logic.

    Coordinates between API layer and repository.
    """

    def __init__(self, repository: ArticleRepository):
        """
        Initialize service with repository.

        Args:
            repository: ArticleRepository implementation
        """
        self.repository = repository

    # ==========================================
    # Public Read Operations
    # ==========================================

    async def get_article(self, slug: str) -> Optional[Article]:
        """
        Get published article by slug (for public API).

        Also increments view count.

        Args:
            slug: Article slug

        Returns:
            Article if found and published, None otherwise
        """
        article = await self.repository.get_by_slug(slug)
        if article and article.is_published:
            # Increment view count (fire-and-forget)
            try:
                await self.repository.increment_view_count(article.id)
            except Exception as e:
                logger.warning(f"[ArticleService] Failed to increment view count: {e}")
            return article
        return None

    async def list_articles(
        self,
        category: Optional[str] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> List[ArticleSummary]:
        """
        List published articles (for public API).

        Args:
            category: Optional category filter (string)
            offset: Pagination offset
            limit: Maximum results

        Returns:
            List of ArticleSummary
        """
        cat = ArticleCategory(category) if category else None
        return await self.repository.list_published(
            category=cat,
            offset=offset,
            limit=limit,
        )

    async def get_article_count(
        self,
        category: Optional[str] = None,
    ) -> int:
        """
        Get published article count.

        Args:
            category: Optional category filter

        Returns:
            Count of published articles
        """
        cat = ArticleCategory(category) if category else None
        return await self.repository.count(category=cat, published_only=True)

    async def get_categories(self) -> List[dict]:
        """
        Get categories with published article counts.

        Returns:
            List of category info dicts
        """
        return await self.repository.get_categories_with_counts()

    async def search_articles(
        self,
        query: str,
        category: Optional[str] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> List[ArticleSummary]:
        """
        Search published articles.

        Args:
            query: Search query
            category: Optional category filter
            offset: Pagination offset
            limit: Maximum results

        Returns:
            List of matching ArticleSummary
        """
        cat = ArticleCategory(category) if category else None
        return await self.repository.search(
            query=query,
            category=cat,
            published_only=True,
            offset=offset,
            limit=limit,
        )

    async def get_featured_articles(
        self,
        category: Optional[str] = None,
        limit: int = 4,
    ) -> List[ArticleSummary]:
        """
        Get featured published articles.

        Args:
            category: Optional category filter (string)
            limit: Maximum results

        Returns:
            List of featured ArticleSummary
        """
        cat = ArticleCategory(category) if category else None
        return await self.repository.list_featured(
            category=cat,
            limit=limit,
        )

    # ==========================================
    # Admin Read Operations
    # ==========================================

    async def admin_get_article(self, article_id: UUID) -> Optional[Article]:
        """
        Get article by ID (for admin API).

        Args:
            article_id: Article UUID

        Returns:
            Article if found, None otherwise
        """
        return await self.repository.get_by_id(article_id)

    async def admin_list_articles(
        self,
        category: Optional[str] = None,
        include_drafts: bool = True,
        offset: int = 0,
        limit: int = 20,
    ) -> List[ArticleSummary]:
        """
        List all articles (for admin API).

        Args:
            category: Optional category filter
            include_drafts: Include unpublished articles
            offset: Pagination offset
            limit: Maximum results

        Returns:
            List of ArticleSummary
        """
        cat = ArticleCategory(category) if category else None
        return await self.repository.list_all(
            category=cat,
            include_drafts=include_drafts,
            offset=offset,
            limit=limit,
        )

    async def admin_get_count(
        self,
        category: Optional[str] = None,
        published_only: bool = False,
    ) -> int:
        """
        Get article count (for admin API).

        Args:
            category: Optional category filter
            published_only: Only count published

        Returns:
            Article count
        """
        cat = ArticleCategory(category) if category else None
        return await self.repository.count(category=cat, published_only=published_only)

    # ==========================================
    # Admin Write Operations
    # ==========================================

    async def create_article(
        self,
        title: str,
        content: str,
        category: str,
        slug: Optional[str] = None,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        cover_image: Optional[str] = None,
        author_id: Optional[str] = None,
        is_published: bool = False,
        sort_order: int = 0,
    ) -> Article:
        """
        Create a new article.

        Args:
            title: Article title
            content: Markdown content
            category: Category string
            slug: Optional custom slug (auto-generated if not provided)
            summary: Optional summary
            tags: Optional list of tags
            cover_image: Optional cover image URL
            author_id: Optional author's user ID
            is_published: Whether to publish immediately
            sort_order: Sort order weight

        Returns:
            Created Article

        Raises:
            ValueError: If slug already exists
        """
        # Generate slug if not provided
        if not slug:
            slug = self._generate_slug(title)

        # Ensure slug is unique
        slug = await self._ensure_unique_slug(slug)

        # Create article entity
        article = Article(
            id=uuid4(),
            slug=slug,
            title=title,
            content=content,
            category=ArticleCategory(category),
            summary=summary,
            tags=tags or [],
            cover_image=cover_image,
            author_id=author_id,
            is_published=is_published,
            published_at=datetime.utcnow() if is_published else None,
            sort_order=sort_order,
            view_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        return await self.repository.create(article)

    async def update_article(
        self,
        article_id: UUID,
        title: Optional[str] = None,
        content: Optional[str] = None,
        category: Optional[str] = None,
        slug: Optional[str] = None,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        cover_image: Optional[str] = None,
        sort_order: Optional[int] = None,
    ) -> Optional[Article]:
        """
        Update an existing article.

        Args:
            article_id: Article UUID
            title: Optional new title
            content: Optional new content
            category: Optional new category
            slug: Optional new slug
            summary: Optional new summary
            tags: Optional new tags
            cover_image: Optional new cover image URL
            sort_order: Optional new sort order

        Returns:
            Updated Article or None if not found

        Raises:
            ValueError: If new slug already exists
        """
        article = await self.repository.get_by_id(article_id)
        if not article:
            return None

        # Update fields if provided
        if title is not None:
            article.title = title
        if content is not None:
            article.content = content
        if category is not None:
            article.category = ArticleCategory(category)
        if slug is not None and slug != article.slug:
            # Check slug uniqueness
            if await self.repository.slug_exists(slug, exclude_id=article_id):
                raise ValueError(f"Slug '{slug}' already exists")
            article.slug = slug
        if summary is not None:
            article.summary = summary
        if tags is not None:
            article.tags = tags
        if cover_image is not None:
            article.cover_image = cover_image
        if sort_order is not None:
            article.sort_order = sort_order

        article.updated_at = datetime.utcnow()

        return await self.repository.update(article)

    async def publish_article(self, article_id: UUID) -> Optional[Article]:
        """
        Publish an article.

        Args:
            article_id: Article UUID

        Returns:
            Updated Article or None if not found
        """
        article = await self.repository.get_by_id(article_id)
        if not article:
            return None

        article.publish()
        article.updated_at = datetime.utcnow()

        return await self.repository.update(article)

    async def unpublish_article(self, article_id: UUID) -> Optional[Article]:
        """
        Unpublish an article (set to draft).

        Args:
            article_id: Article UUID

        Returns:
            Updated Article or None if not found
        """
        article = await self.repository.get_by_id(article_id)
        if not article:
            return None

        article.unpublish()
        article.updated_at = datetime.utcnow()

        return await self.repository.update(article)

    async def delete_article(self, article_id: UUID) -> bool:
        """
        Delete an article.

        Args:
            article_id: Article UUID

        Returns:
            True if deleted, False if not found
        """
        return await self.repository.delete(article_id)

    # ==========================================
    # Helper Methods
    # ==========================================

    def _generate_slug(self, title: str) -> str:
        """
        Generate URL-friendly slug from title.

        Args:
            title: Article title

        Returns:
            Slug string
        """
        # Convert to lowercase
        slug = title.lower()
        # Replace spaces with hyphens
        slug = re.sub(r'\s+', '-', slug)
        # Remove special characters
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        # Remove consecutive hyphens
        slug = re.sub(r'-+', '-', slug)
        # Trim hyphens from ends
        slug = slug.strip('-')
        # Limit length
        return slug[:200]

    async def _ensure_unique_slug(self, slug: str, exclude_id: Optional[UUID] = None) -> str:
        """
        Ensure slug is unique by appending number if necessary.

        Args:
            slug: Base slug
            exclude_id: Optional article ID to exclude

        Returns:
            Unique slug
        """
        if not await self.repository.slug_exists(slug, exclude_id):
            return slug

        # Append number until unique
        counter = 1
        while True:
            new_slug = f"{slug}-{counter}"
            if not await self.repository.slug_exists(new_slug, exclude_id):
                return new_slug
            counter += 1
            if counter > 100:
                # Safety limit
                new_slug = f"{slug}-{uuid4().hex[:8]}"
                return new_slug
