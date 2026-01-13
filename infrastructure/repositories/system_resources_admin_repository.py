"""
SystemResources Admin Repository - Data access for Admin System Resources API.

@module infrastructure.repositories.system_resources_admin_repository
@version 2.0.0 (AsyncClient migration)

Changes in v2.0:
- Removed lazy loading (client parameter now mandatory)
- All methods use AsyncClient
- Removed get_supabase_client() import (sync client)

Purpose:
- Admin-specific data access for system_resources table
- Returns raw Dict data (not domain objects) for CRUD operations
- Supports file metadata, audit logs, and batch operations
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone

from core.database import DatabaseClient
from core.database.retry import retry_on_network_error


class SupabaseSystemResourcesAdminRepository:
    """
    Supabase implementation for Admin System Resources data access.

    v2.0: AsyncClient required (no lazy loading).

    Unlike SupabaseSystemResourceRepository (user-facing),
    this repository is for admin CRUD operations returning raw data.
    """

    def __init__(self, db_client: DatabaseClient):
        """
        Initialize repository with AsyncClient.

        Args:
            db_client: AsyncClient instance (required)

        Raises:
            ValueError: If db_client is None
        """
        if db_client is None:
            raise ValueError("AsyncClient required for SupabaseSystemResourcesAdminRepository")
        self._client = db_client

    @property
    def client(self):
        """Get AsyncClient instance."""
        return self._client

    @retry_on_network_error()
    async def list_resources(
        self,
        resource_type: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List system resources with filters and pagination.

        Args:
            resource_type: Filter by resource type
            category: Filter by category
            is_active: Filter by active status
            search: Search in name/description (pre-sanitized)
            limit: Max items to return
            offset: Items to skip

        Returns:
            Tuple of (items list, total count)
        """
        query = self.client.table("system_resources").select("*", count="exact")

        if resource_type:
            query = query.eq("resource_type", resource_type)
        if category:
            query = query.eq("category", category)
        if is_active is not None:
            query = query.eq("is_active", is_active)
        if search:
            # Search query is pre-sanitized by API layer
            query = query.or_(f"name.ilike.%{search}%,description.ilike.%{search}%")

        query = query.order("sort_order", desc=False).order("created_at", desc=True)
        query = query.range(offset, offset + limit - 1)

        result = await query.execute()

        return (result.data or [], result.count or 0)

    @retry_on_network_error()
    async def get_by_id(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """
        Get single resource by ID.

        Args:
            resource_id: Resource UUID

        Returns:
            Resource dict or None if not found
        """
        result = await self.client.table("system_resources")\
            .select("*")\
            .eq("id", resource_id)\
            .single()\
            .execute()

        return result.data if result.data else None

    @retry_on_network_error()
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new resource.

        Args:
            data: Resource data dict

        Returns:
            Created resource dict

        Raises:
            Exception: If creation fails
        """
        result = await self.client.table("system_resources").insert(data).execute()

        if not result.data:
            raise Exception("Failed to create resource record")

        return result.data[0]

    @retry_on_network_error()
    async def update(
        self,
        resource_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update resource metadata.

        Args:
            resource_id: Resource UUID
            updates: Fields to update

        Returns:
            Updated resource dict

        Raises:
            Exception: If update fails
        """
        result = await self.client.table("system_resources")\
            .update(updates)\
            .eq("id", resource_id)\
            .execute()

        if not result.data:
            raise Exception("Failed to update resource")

        return result.data[0]

    @retry_on_network_error()
    async def soft_delete(self, resource_id: str, admin_id: str) -> bool:
        """
        Soft delete resource (deactivate only).

        Args:
            resource_id: Resource UUID
            admin_id: Admin performing action

        Returns:
            True if successful
        """
        await self.client.table("system_resources")\
            .update({
                "is_active": False,
                "updated_by": admin_id,
                "updated_at": "now()"
            })\
            .eq("id", resource_id)\
            .execute()

        return True

    @retry_on_network_error()
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get resource statistics.

        Returns:
            Dict with total, active, inactive, and by_type breakdown
        """
        # Count active vs inactive
        active_count = await self.client.table("system_resources")\
            .select("id", count="exact")\
            .eq("is_active", True)\
            .execute()

        inactive_count = await self.client.table("system_resources")\
            .select("id", count="exact")\
            .eq("is_active", False)\
            .execute()

        # Group by type
        all_resources = await self.client.table("system_resources")\
            .select("resource_type, is_active")\
            .execute()

        type_breakdown = {}
        for r in all_resources.data or []:
            t = r.get("resource_type", "unknown")
            if t not in type_breakdown:
                type_breakdown[t] = {"total": 0, "active": 0, "inactive": 0}
            type_breakdown[t]["total"] += 1
            if r.get("is_active"):
                type_breakdown[t]["active"] += 1
            else:
                type_breakdown[t]["inactive"] += 1

        return {
            "total": (active_count.count or 0) + (inactive_count.count or 0),
            "active": active_count.count or 0,
            "inactive": inactive_count.count or 0,
            "by_type": type_breakdown
        }

    @retry_on_network_error()
    async def get_audit_log(
        self,
        resource_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get audit log for a resource.

        Args:
            resource_id: Resource UUID
            limit: Max items to return

        Returns:
            List of audit log entries
        """
        result = await self.client.table("system_resource_audit_logs")\
            .select("*")\
            .eq("resource_id", resource_id)\
            .order("changed_at", desc=True)\
            .limit(limit)\
            .execute()

        return result.data or []

    @retry_on_network_error()
    async def batch_update(
        self,
        resource_ids: List[str],
        updates: Dict[str, Any]
    ) -> int:
        """
        Batch update multiple resources.

        Args:
            resource_ids: List of resource UUIDs
            updates: Fields to update

        Returns:
            Number of updated resources
        """
        await self.client.table("system_resources")\
            .update(updates)\
            .in_("id", resource_ids)\
            .execute()

        return len(resource_ids)
