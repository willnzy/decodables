"""
Category Repository Interface.

@module domains.content.category_repository
@version 1.0.0
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime


class ICategoryRepository(ABC):
    """Repository interface for Asset Category management."""

    @abstractmethod
    async def get_by_id(self, category_id: str) -> Optional[Dict[str, Any]]:
        """
        Get category by ID.

        Args:
            category_id: Category UUID

        Returns:
            Category dict or None if not found
        """
        pass

    @abstractmethod
    async def get_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """
        Get category by slug.

        Args:
            slug: Category slug (unique identifier)

        Returns:
            Category dict or None if not found
        """
        pass

    @abstractmethod
    async def get_all(
        self,
        asset_type: Optional[str] = None,
        parent_id: Optional[str] = None,
        is_visible: Optional[bool] = None,
        min_tier: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all categories with optional filtering.

        Args:
            asset_type: Filter by asset type (text/image/shape/etc.)
            parent_id: Filter by parent category
            is_visible: Filter by visibility status
            min_tier: Filter by minimum tier requirement
            limit: Maximum results to return
            offset: Results to skip for pagination

        Returns:
            List of category dicts
        """
        pass

    @abstractmethod
    async def get_tree(
        self,
        asset_type: Optional[str] = None,
        include_hidden: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get category tree using LTREE path queries.

        Args:
            asset_type: Filter by asset type
            include_hidden: Include is_visible=False categories

        Returns:
            List of categories in tree order (ordered by path)
        """
        pass

    @abstractmethod
    async def get_children(
        self,
        parent_slug: str,
        recursive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get child categories of a parent.

        Args:
            parent_slug: Parent category slug
            recursive: If True, get all descendants; if False, only direct children

        Returns:
            List of child category dicts
        """
        pass

    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new category.

        Args:
            data: Category data dict including:
                - slug: str
                - name: str
                - asset_type: str
                - parent_id: Optional[str]
                - path: str (LTREE format)
                - level: int
                - min_tier: str (default 't1')
                - is_visible: bool (default True)
                - display_order: int (default 0)

        Returns:
            Created category dict

        Raises:
            Exception: If creation fails
        """
        pass

    @abstractmethod
    async def update(
        self,
        category_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update category metadata.

        Args:
            category_id: Category UUID
            updates: Fields to update (name, icon, description, etc.)

        Returns:
            Updated category dict

        Raises:
            Exception: If update fails
        """
        pass

    @abstractmethod
    async def move_category(
        self,
        category_slug: str,
        new_parent_slug: Optional[str],
        new_path: str,
        new_level: int
    ) -> Dict[str, Any]:
        """
        Move a category to a new parent and update path/level.

        Args:
            category_slug: Category to move
            new_parent_slug: New parent category (None for root)
            new_path: New LTREE path
            new_level: New level (1-3)

        Returns:
            Updated category dict

        Raises:
            Exception: If move would create circular reference
        """
        pass

    @abstractmethod
    async def update_descendants_path(
        self,
        old_path: str,
        new_path: str
    ) -> int:
        """
        Update all descendant categories when parent path changes.

        Args:
            old_path: Original LTREE path
            new_path: New LTREE path

        Returns:
            Number of updated categories
        """
        pass

    @abstractmethod
    async def delete(self, category_id: str, cascade: bool = False) -> bool:
        """
        Delete a category (soft delete).

        Args:
            category_id: Category UUID
            cascade: If True, delete all descendants; if False, fail if has children

        Returns:
            True if deleted

        Raises:
            Exception: If cascade=False and category has children
        """
        pass

    @abstractmethod
    async def count_by_asset_type(self) -> Dict[str, int]:
        """
        Count categories grouped by asset type.

        Returns:
            Dict of {asset_type: count}
        """
        pass

    @abstractmethod
    async def update_asset_count(self, category_id: str, count: int) -> bool:
        """
        Update the asset_count field for a category.

        Args:
            category_id: Category UUID
            count: New asset count

        Returns:
            True if updated
        """
        pass

    @abstractmethod
    async def increment_usage_count(self, category_id: str) -> bool:
        """
        Increment the usage_count field by 1.

        Args:
            category_id: Category UUID

        Returns:
            True if incremented
        """
        pass
