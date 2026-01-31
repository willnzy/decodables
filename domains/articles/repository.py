"""
Article Repository Interface.

@module domains.articles.repository
@version 1.0.0

Abstract repository interface following DDD principles.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from .entities import Article, ArticleSummary, ArticleCategory


class ArticleRepository(ABC):
    """
    Abstract repository interface for Article persistence.

    Implementations should handle the actual database operations.
    """

    # ==========================================
    # Read Operations
    # ==========================================

    @abstractmethod
    async def get_by_id(self, article_id: UUID) -> Optional[Article]:
        """
        Get article by ID.

        Args:
            article_id: Article UUID

        Returns:
            Article entity or None if not found
        """
        pass

    @abstractmethod
    async def get_by_slug(self, slug: str) -> Optional[Article]:
        """
        Get article by slug.

        Args:
            slug: URL-friendly identifier

        Returns:
            Article entity or None if not found
        """
        pass

    @abstractmethod
    async def list_published(
        self,
        category: Optional[ArticleCategory] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> List[ArticleSummary]:
        """
        List published articles.

        Args:
            category: Optional category filter
            offset: Pagination offset
            limit: Maximum number of results

        Returns:
            List of ArticleSummary (without full content)
        """
        pass

    @abstractmethod
    async def list_all(
        self,
        category: Optional[ArticleCategory] = None,
        include_drafts: bool = True,
        offset: int = 0,
        limit: int = 20,
    ) -> List[ArticleSummary]:
        """
        List all articles (for admin).

        Args:
            category: Optional category filter
            include_drafts: Include unpublished articles
            offset: Pagination offset
            limit: Maximum number of results

        Returns:
            List of ArticleSummary
        """
        pass

    @abstractmethod
    async def count(
        self,
        category: Optional[ArticleCategory] = None,
        published_only: bool = False,
    ) -> int:
        """
        Count articles.

        Args:
            category: Optional category filter
            published_only: Only count published articles

        Returns:
            Article count
        """
        pass

    @abstractmethod
    async def get_categories_with_counts(self) -> List[dict]:
        """
        Get all categories with their article counts.

        Returns:
            List of {"category": str, "count": int, "published_count": int}
        """
        pass

    @abstractmethod
    async def list_featured(
        self,
        category: Optional[ArticleCategory] = None,
        limit: int = 4,
    ) -> List[ArticleSummary]:
        """
        List featured published articles.

        Args:
            category: Optional category filter
            limit: Maximum number of results

        Returns:
            List of featured ArticleSummary (is_featured=true, is_published=true)
        """
        pass

    # ==========================================
    # Write Operations
    # ==========================================

    @abstractmethod
    async def create(self, article: Article) -> Article:
        """
        Create a new article.

        Args:
            article: Article entity to create

        Returns:
            Created article with generated ID
        """
        pass

    @abstractmethod
    async def update(self, article: Article) -> Article:
        """
        Update an existing article.

        Args:
            article: Article entity with updated fields

        Returns:
            Updated article
        """
        pass

    @abstractmethod
    async def delete(self, article_id: UUID) -> bool:
        """
        Soft delete an article (sets is_deleted=true).

        Args:
            article_id: Article UUID to soft delete

        Returns:
            True if soft-deleted, False if not found
        """
        pass

    @abstractmethod
    async def hard_delete(self, article_id: UUID) -> bool:
        """
        Permanently delete an article (for data cleanup only).

        Args:
            article_id: Article UUID to permanently delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def increment_view_count(self, article_id: UUID) -> bool:
        """
        Increment article view count.

        Args:
            article_id: Article UUID

        Returns:
            True if successful
        """
        pass

    # ==========================================
    # Search Operations
    # ==========================================

    @abstractmethod
    async def search(
        self,
        query: str,
        category: Optional[ArticleCategory] = None,
        published_only: bool = True,
        offset: int = 0,
        limit: int = 20,
    ) -> List[ArticleSummary]:
        """
        Search articles by title and content.

        Args:
            query: Search query string
            category: Optional category filter
            published_only: Only search published articles
            offset: Pagination offset
            limit: Maximum number of results

        Returns:
            List of matching ArticleSummary
        """
        pass

    @abstractmethod
    async def slug_exists(self, slug: str, exclude_id: Optional[UUID] = None) -> bool:
        """
        Check if a slug already exists.

        Args:
            slug: Slug to check
            exclude_id: Optional article ID to exclude (for updates)

        Returns:
            True if slug exists
        """
        pass
