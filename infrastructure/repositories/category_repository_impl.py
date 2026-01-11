"""
Category Repository Implementation using Supabase.

@module infrastructure.repositories.category_repository_impl
@version 1.0.0
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from core.database import DatabaseClient
from core.database.retry import retry_on_network_error
from domains.content.category_repository import ICategoryRepository


class SupabaseCategoryRepository(ICategoryRepository):
    """
    Supabase implementation for Asset Category repository.

    Handles LTREE queries for hierarchical category structure.
    """

    def __init__(self, db_client: DatabaseClient):
        """
        Initialize repository with database client.

        Args:
            db_client: Supabase database client
        """
        self._client = db_client

    @property
    def client(self):
        """Get database client."""
        if self._client is None:
            from core.database import get_supabase_client
            self._client = get_supabase_client()
        return self._client

    @retry_on_network_error()
    async def get_by_id(self, category_id: str) -> Optional[Dict[str, Any]]:
        """Get category by ID."""
        result = self.client.table("asset_categories")\
            .select("*")\
            .eq("id", category_id)\
            .is_("deleted_at", "null")\
            .single()\
            .execute()

        return result.data if result.data else None

    @retry_on_network_error()
    async def get_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get category by slug."""
        result = self.client.table("asset_categories")\
            .select("*")\
            .eq("slug", slug)\
            .is_("deleted_at", "null")\
            .single()\
            .execute()

        return result.data if result.data else None

    @retry_on_network_error()
    async def get_all(
        self,
        asset_type: Optional[str] = None,
        parent_id: Optional[str] = None,
        is_visible: Optional[bool] = None,
        min_tier: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all categories with optional filtering."""
        query = self.client.table("asset_categories")\
            .select("*")\
            .is_("deleted_at", "null")

        if asset_type:
            query = query.eq("asset_type", asset_type)
        if parent_id:
            query = query.eq("parent_id", parent_id)
        if is_visible is not None:
            query = query.eq("is_visible", is_visible)
        if min_tier:
            query = query.eq("min_tier", min_tier)

        query = query.order("path", desc=False)\
                     .order("display_order", desc=False)\
                     .range(offset, offset + limit - 1)

        result = query.execute()
        return result.data or []

    @retry_on_network_error()
    async def get_tree(
        self,
        asset_type: Optional[str] = None,
        include_hidden: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get category tree using LTREE path queries.

        Categories are ordered by path for tree structure.
        """
        query = self.client.table("asset_categories")\
            .select("*")\
            .is_("deleted_at", "null")

        if asset_type:
            query = query.eq("asset_type", asset_type)
        if not include_hidden:
            query = query.eq("is_visible", True)

        query = query.order("path", desc=False)\
                     .order("display_order", desc=False)

        result = query.execute()
        return result.data or []

    @retry_on_network_error()
    async def get_children(
        self,
        parent_slug: str,
        recursive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get child categories of a parent.

        Uses LTREE queries for efficient hierarchical retrieval.
        """
        # First get the parent category to find its path
        parent = await self.get_by_slug(parent_slug)
        if not parent:
            return []

        parent_path = parent.get("path")
        if not parent_path:
            return []

        if recursive:
            # Get all descendants using LTREE <@ operator
            # This uses PostgreSQL RPC for LTREE queries
            result = self.client.rpc(
                "get_category_descendants",
                {"parent_path_input": parent_path}
            ).execute()
            return result.data or []
        else:
            # Get only direct children
            result = self.client.table("asset_categories")\
                .select("*")\
                .eq("parent_id", parent["id"])\
                .is_("deleted_at", "null")\
                .order("display_order", desc=False)\
                .execute()
            return result.data or []

    @retry_on_network_error()
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]]:
        """Create a new category."""
        result = self.client.table("asset_categories").insert(data).execute()

        if not result.data:
            raise Exception("Failed to create category")

        return result.data[0]

    @retry_on_network_error()
    async def update(
        self,
        category_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update category metadata."""
        # Add updated_at timestamp
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        result = self.client.table("asset_categories")\
            .update(updates)\
            .eq("id", category_id)\
            .execute()

        if not result.data:
            raise Exception("Failed to update category")

        return result.data[0]

    @retry_on_network_error()
    async def move_category(
        self,
        category_slug: str,
        new_parent_slug: Optional[str],
        new_path: str,
        new_level: int
    ) -> Dict[str, Any]:
        """Move a category to a new parent and update path/level."""
        category = await self.get_by_slug(category_slug)
        if not category:
            raise Exception(f"Category not found: {category_slug}")

        # Get new parent ID if provided
        new_parent_id = None
        if new_parent_slug:
            new_parent = await self.get_by_slug(new_parent_slug)
            if not new_parent:
                raise Exception(f"Parent category not found: {new_parent_slug}")
            new_parent_id = new_parent["id"]

            # Check for circular reference
            if new_path.startswith(category["path"] + "."):
                raise Exception("Cannot move category to its own descendant")

        # Update category
        updates = {
            "parent_id": new_parent_id,
            "path": new_path,
            "level": new_level,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        result = self.client.table("asset_categories")\
            .update(updates)\
            .eq("id", category["id"])\
            .execute()

        if not result.data:
            raise Exception("Failed to move category")

        return result.data[0]

    @retry_on_network_error()
    async def update_descendants_path(
        self,
        old_path: str,
        new_path: str
    ) -> int:
        """
        Update all descendant categories when parent path changes.

        Uses PostgreSQL RPC function for efficient LTREE path updates.
        """
        result = self.client.rpc(
            "update_category_descendants_path",
            {
                "old_path_input": old_path,
                "new_path_input": new_path
            }
        ).execute()

        # RPC returns count of updated rows
        return result.data if result.data else 0

    @retry_on_network_error()
    async def delete(self, category_id: str, cascade: bool = False) -> bool:
        """Delete a category (soft delete)."""
        if not cascade:
            # Check if category has children
            result = self.client.table("asset_categories")\
                .select("id")\
                .eq("parent_id", category_id)\
                .is_("deleted_at", "null")\
                .limit(1)\
                .execute()

            if result.data:
                raise Exception(
                    "Cannot delete category with children. "
                    "Use cascade=True to delete all descendants."
                )

        # Soft delete
        now = datetime.now(timezone.utc)
        updates = {
            "deleted_at": now.isoformat(),
            "recovery_expires_at": (now.replace(day=now.day + 30)).isoformat(),
            "updated_at": now.isoformat()
        }

        self.client.table("asset_categories")\
            .update(updates)\
            .eq("id", category_id)\
            .execute()

        if cascade:
            # Soft delete all descendants
            category = await self.get_by_id(category_id)
            if category:
                # Use RPC to delete all descendants
                self.client.rpc(
                    "soft_delete_category_descendants",
                    {"parent_path_input": category["path"]}
                ).execute()

        return True

    @retry_on_network_error()
    async def count_by_asset_type(self) -> Dict[str, int]:
        """Count categories grouped by asset type."""
        result = self.client.table("asset_categories")\
            .select("asset_type")\
            .is_("deleted_at", "null")\
            .execute()

        counts = {}
        for row in (result.data or []):
            asset_type = row.get("asset_type", "unknown")
            counts[asset_type] = counts.get(asset_type, 0) + 1

        return counts

    @retry_on_network_error()
    async def update_asset_count(self, category_id: str, count: int) -> bool:
        """Update the asset_count field for a category."""
        self.client.table("asset_categories")\
            .update({
                "asset_count": count,
                "updated_at": datetime.now(timezone.utc).isoformat()
            })\
            .eq("id", category_id)\
            .execute()

        return True

    @retry_on_network_error()
    async def increment_usage_count(self, category_id: str) -> bool:
        """Increment the usage_count field by 1."""
        # Use PostgreSQL increment RPC
        self.client.rpc(
            "increment_category_usage",
            {"category_id_input": category_id}
        ).execute()

        return True
