"""
Category Query Handlers - CQRS Query Side.

@module application.queries.categories
@version 1.0.0
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from domains.content.category_service import CategoryService


# =============================================================================
# Query DTOs
# =============================================================================

@dataclass
class GetCategoryTreeQuery:
    """Query to get category tree."""
    asset_type: Optional[str] = None
    include_hidden: bool = False


@dataclass
class GetCategoryQuery:
    """Query to get a single category."""
    category_id: Optional[str] = None
    slug: Optional[str] = None


@dataclass
class ListCategoriesQuery:
    """Query to list categories with filters."""
    asset_type: Optional[str] = None
    parent_id: Optional[str] = None
    is_visible: Optional[bool] = None
    min_tier: Optional[str] = None
    limit: int = 100
    offset: int = 0


@dataclass
class GetChildCategoriesQuery:
    """Query to get child categories."""
    parent_slug: str
    recursive: bool = False


@dataclass
class GetCategoryStatsQuery:
    """Query to get category statistics."""
    pass  # No parameters needed


# =============================================================================
# Query Handlers
# =============================================================================

class CategoryQueryHandlers:
    """Handles category query operations."""

    def __init__(self, category_service: CategoryService):
        """
        Initialize handlers with service.

        Args:
            category_service: Category business logic service
        """
        self.service = category_service

    async def handle_get_category_tree(
        self,
        query: GetCategoryTreeQuery
    ) -> List[Dict[str, Any]]:
        """
        Handle get category tree query.

        Args:
            query: GetCategoryTreeQuery

        Returns:
            List of categories in tree order
        """
        return await self.service.get_category_tree(
            asset_type=query.asset_type,
            include_hidden=query.include_hidden
        )

    async def handle_get_category(
        self,
        query: GetCategoryQuery
    ) -> Optional[Dict[str, Any]]:
        """
        Handle get single category query.

        Args:
            query: GetCategoryQuery (must have either category_id or slug)

        Returns:
            Category dict or None

        Raises:
            ValueError: If neither category_id nor slug provided
        """
        if query.category_id:
            return await self.service.get_category_by_id(query.category_id)
        elif query.slug:
            return await self.service.get_category_by_slug(query.slug)
        else:
            raise ValueError("Must provide either category_id or slug")

    async def handle_list_categories(
        self,
        query: ListCategoriesQuery
    ) -> List[Dict[str, Any]]:
        """
        Handle list categories query.

        Args:
            query: ListCategoriesQuery

        Returns:
            List of categories
        """
        return await self.service.list_categories(
            asset_type=query.asset_type,
            parent_id=query.parent_id,
            is_visible=query.is_visible,
            min_tier=query.min_tier,
            limit=query.limit,
            offset=query.offset
        )

    async def handle_get_child_categories(
        self,
        query: GetChildCategoriesQuery
    ) -> List[Dict[str, Any]]:
        """
        Handle get child categories query.

        Args:
            query: GetChildCategoriesQuery

        Returns:
            List of child categories
        """
        return await self.service.get_children(
            parent_slug=query.parent_slug,
            recursive=query.recursive
        )

    async def handle_get_category_stats(
        self,
        query: GetCategoryStatsQuery
    ) -> Dict[str, Any]:
        """
        Handle get category statistics query.

        Args:
            query: GetCategoryStatsQuery

        Returns:
            Statistics dict with total and by_asset_type
        """
        return await self.service.get_category_stats()
