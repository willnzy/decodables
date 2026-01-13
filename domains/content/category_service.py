"""
Category Service - Business logic for category management.

@module domains.content.category_service
@version 1.0.0
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid

from domains.content.repository import ICategoryRepository


class CategoryService:
    """
    Category management business logic.

    Handles category creation, updates, movement, deletion,
    and tree operations with LTREE path management.
    """

    def __init__(self, repository: ICategoryRepository):
        """
        Initialize service with repository.

        Args:
            repository: Category repository implementation
        """
        self.repository = repository

    async def get_category_by_id(self, category_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a category by ID.

        Args:
            category_id: Category UUID

        Returns:
            Category dict or None
        """
        return await self.repository.get_by_id(category_id)

    async def get_category_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """
        Get a category by slug.

        Args:
            slug: Category slug

        Returns:
            Category dict or None
        """
        return await self.repository.get_by_slug(slug)

    async def get_category_tree(
        self,
        asset_type: Optional[str] = None,
        include_hidden: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get category tree (LTREE query).

        Categories are returned in tree order (ordered by path).

        Args:
            asset_type: Filter by asset type
            include_hidden: Include is_visible=False categories

        Returns:
            List of categories in tree order
        """
        return await self.repository.get_tree(
            asset_type=asset_type,
            include_hidden=include_hidden
        )

    async def get_children(
        self,
        parent_slug: str,
        recursive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get child categories of a parent.

        Args:
            parent_slug: Parent category slug
            recursive: If True, get all descendants

        Returns:
            List of child categories
        """
        return await self.repository.get_children(
            parent_slug=parent_slug,
            recursive=recursive
        )

    async def list_categories(
        self,
        asset_type: Optional[str] = None,
        parent_id: Optional[str] = None,
        is_visible: Optional[bool] = None,
        min_tier: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List categories with filtering and pagination.

        Args:
            asset_type: Filter by asset type
            parent_id: Filter by parent
            is_visible: Filter by visibility
            min_tier: Filter by tier requirement
            limit: Max results
            offset: Results to skip

        Returns:
            List of categories
        """
        return await self.repository.get_all(
            asset_type=asset_type,
            parent_id=parent_id,
            is_visible=is_visible,
            min_tier=min_tier,
            limit=limit,
            offset=offset
        )

    async def create_category(
        self,
        slug: str,
        name: str,
        asset_type: str,
        parent_slug: Optional[str] = None,
        name_i18n: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        min_tier: str = "t1",
        is_visible: bool = True,
        is_featured: bool = False,
        display_order: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new category.

        Automatically calculates path and level based on parent.

        Args:
            slug: Unique slug identifier
            name: Display name
            asset_type: Asset type (text/image/shape/etc.)
            parent_slug: Parent category slug (None for root)
            name_i18n: Internationalized names
            description: Category description
            icon: Icon identifier
            min_tier: Minimum tier requirement (t1/t2/t3)
            is_visible: Visibility status
            is_featured: Featured status
            display_order: Sort order
            metadata: Additional metadata

        Returns:
            Created category dict

        Raises:
            ValueError: If parent not found or invalid data
            Exception: If creation fails
        """
        # Validate slug format
        if not slug or not slug.replace('-', '').replace('_', '').isalnum():
            raise ValueError(
                "Slug must contain only alphanumeric characters, hyphens, and underscores"
            )

        # Check if slug already exists
        existing = await self.repository.get_by_slug(slug)
        if existing:
            raise ValueError(f"Category with slug '{slug}' already exists")

        # Validate asset_type
        valid_types = {'text', 'image', 'shape', 'table', 'sticker', 'icon', 'frame'}
        if asset_type not in valid_types:
            raise ValueError(
                f"Invalid asset_type. Must be one of: {', '.join(valid_types)}"
            )

        # Validate min_tier
        if min_tier not in {'t1', 't2', 't3'}:
            raise ValueError("min_tier must be one of: t1, t2, t3")

        # Calculate path and level based on parent
        parent_id = None
        path = slug
        level = 1

        if parent_slug:
            parent = await self.repository.get_by_slug(parent_slug)
            if not parent:
                raise ValueError(f"Parent category not found: {parent_slug}")

            parent_id = parent["id"]
            parent_path = parent["path"]
            parent_level = parent["level"]

            # Check level limit (max 3 levels)
            if parent_level >= 3:
                raise ValueError("Cannot create category: maximum level (3) reached")

            path = f"{parent_path}.{slug}"
            level = parent_level + 1

        # Build category data
        category_data = {
            "id": str(uuid.uuid4()),
            "parent_id": parent_id,
            "path": path,
            "level": level,
            "slug": slug,
            "name": name,
            "name_i18n": name_i18n or {},
            "description": description,
            "icon": icon,
            "asset_type": asset_type,
            "is_visible": is_visible,
            "is_featured": is_featured,
            "display_order": display_order,
            "min_tier": min_tier,
            "metadata": metadata or {},
            "asset_count": 0,
            "usage_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        return await self.repository.create(category_data)

    async def update_category(
        self,
        category_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update category metadata.

        Note: Use move_category() to change parent/path/level.

        Args:
            category_id: Category UUID
            updates: Fields to update (name, icon, description, etc.)

        Returns:
            Updated category dict

        Raises:
            ValueError: If trying to update protected fields
            Exception: If update fails
        """
        # Protected fields that cannot be updated via this method
        protected_fields = {'id', 'parent_id', 'path', 'level', 'slug', 'created_at'}

        for field in protected_fields:
            if field in updates:
                raise ValueError(
                    f"Cannot update '{field}' via update_category(). "
                    f"Use move_category() to change hierarchy."
                )

        # Validate asset_type if provided
        if 'asset_type' in updates:
            valid_types = {'text', 'image', 'shape', 'table', 'sticker', 'icon', 'frame'}
            if updates['asset_type'] not in valid_types:
                raise ValueError(
                    f"Invalid asset_type. Must be one of: {', '.join(valid_types)}"
                )

        # Validate min_tier if provided
        if 'min_tier' in updates:
            if updates['min_tier'] not in {'t1', 't2', 't3'}:
                raise ValueError("min_tier must be one of: t1, t2, t3")

        return await self.repository.update(category_id, updates)

    async def move_category(
        self,
        category_slug: str,
        new_parent_slug: Optional[str]
    ) -> Dict[str, Any]:
        """
        Move a category to a new parent.

        Automatically updates path, level, and all descendant categories.

        Args:
            category_slug: Category to move
            new_parent_slug: New parent category (None to move to root)

        Returns:
            Updated category dict

        Raises:
            ValueError: If would create circular reference or exceed max level
            Exception: If move fails
        """
        # Get category to move
        category = await self.repository.get_by_slug(category_slug)
        if not category:
            raise ValueError(f"Category not found: {category_slug}")

        old_path = category["path"]
        old_level = category["level"]

        # Calculate new path and level
        if new_parent_slug is None:
            # Moving to root
            new_path = category_slug
            new_level = 1
        else:
            # Moving to new parent
            new_parent = await self.repository.get_by_slug(new_parent_slug)
            if not new_parent:
                raise ValueError(f"Parent category not found: {new_parent_slug}")

            # Check for circular reference
            new_parent_path = new_parent["path"]
            if new_parent_path.startswith(f"{old_path}."):
                raise ValueError(
                    "Cannot move category to its own descendant (circular reference)"
                )

            # Check level limit
            new_level = new_parent["level"] + 1
            level_increase = new_level - old_level

            if new_level > 3:
                raise ValueError("Cannot move category: would exceed maximum level (3)")

            # Check if any descendants would exceed max level
            descendants = await self.repository.get_children(
                parent_slug=category_slug,
                recursive=True
            )
            for desc in descendants:
                if desc["level"] + level_increase > 3:
                    raise ValueError(
                        "Cannot move category: descendants would exceed maximum level (3)"
                    )

            new_path = f"{new_parent_path}.{category_slug}"

        # Move category
        updated_category = await self.repository.move_category(
            category_slug=category_slug,
            new_parent_slug=new_parent_slug,
            new_path=new_path,
            new_level=new_level
        )

        # Update all descendants if path changed
        if old_path != new_path:
            await self.repository.update_descendants_path(
                old_path=old_path,
                new_path=new_path
            )

        return updated_category

    async def delete_category(
        self,
        category_id: str,
        cascade: bool = False
    ) -> bool:
        """
        Delete a category (soft delete).

        Args:
            category_id: Category UUID
            cascade: If True, delete all descendants; if False, fail if has children

        Returns:
            True if deleted

        Raises:
            ValueError: If cascade=False and category has children
            Exception: If deletion fails
        """
        return await self.repository.delete(category_id, cascade=cascade)

    async def reorder_categories(
        self,
        category_orders: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Reorder multiple categories.

        Args:
            category_orders: List of {id: str, display_order: int}

        Returns:
            List of updated categories

        Raises:
            ValueError: If invalid data
            Exception: If update fails
        """
        updated_categories = []

        for item in category_orders:
            category_id = item.get("id")
            display_order = item.get("display_order")

            if not category_id or display_order is None:
                raise ValueError("Each item must have 'id' and 'display_order'")

            updated = await self.repository.update(
                category_id=category_id,
                updates={"display_order": display_order}
            )
            updated_categories.append(updated)

        return updated_categories

    async def get_category_stats(self) -> Dict[str, Any]:
        """
        Get category statistics.

        Returns:
            Dict with count by asset_type
        """
        counts = await self.repository.count_by_asset_type()

        return {
            "total": sum(counts.values()),
            "by_asset_type": counts
        }

    async def update_asset_count(self, category_id: str, count: int) -> bool:
        """
        Update asset count for a category.

        Args:
            category_id: Category UUID
            count: New asset count

        Returns:
            True if updated
        """
        return await self.repository.update_asset_count(category_id, count)

    async def increment_usage(self, category_id: str) -> bool:
        """
        Increment usage count for a category.

        Args:
            category_id: Category UUID

        Returns:
            True if incremented
        """
        return await self.repository.increment_usage_count(category_id)
