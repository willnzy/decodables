"""
SystemResource Repository Implementation - Supabase.

@module infrastructure.repositories.system_resource_repository
@version 1.0.0
"""

from typing import Optional, List
from datetime import datetime, timezone

from core.database import DatabaseClient
from domains.content import (
    SystemResource,
    ISystemResourceRepository,
    ResourceType,
    ResourceCategory,
    ResourceMetadata,
    AccessControl,
)


class SupabaseSystemResourceRepository(ISystemResourceRepository):
    """Supabase implementation of SystemResource repository."""

    def __init__(self, client: DatabaseClient):
        """
        Initialize repository with database client.

        Args:
            client: Supabase database client
        """
        self.client = client

    async def get_by_id(self, resource_id: str) -> Optional[SystemResource]:
        """Get resource by ID."""
        result = self.client.table("system_resources").select("*").eq(
            "id", resource_id
        ).single().execute()

        if not result.data:
            return None

        return self._map_to_domain(result.data)

    async def get_all(
        self,
        resource_type: Optional[ResourceType] = None,
        category: Optional[ResourceCategory] = None,
        allowed_tiers_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[SystemResource]:
        """Get all resources with filtering."""
        query = self.client.table("system_resources").select("*")

        if resource_type:
            query = query.eq("type", resource_type.value)

        if category:
            query = query.eq("category", category.value)

        if allowed_tiers_filter:
            # Use contains for array column
            query = query.contains("allowed_tiers", [allowed_tiers_filter])

        query = query.order("created_at", desc=True)
        query = query.range(offset, offset + limit - 1)

        result = query.execute()

        return [self._map_to_domain(row) for row in (result.data or [])]

    async def create(self, resource: SystemResource) -> SystemResource:
        """Create a new resource."""
        data = {
            "id": resource.resource_id,
            "type": resource.resource_type.value,
            "url": resource.url,
            "category": resource.category.value if resource.category else None,
            "allowed_tiers": resource.access_control.allowed_tiers,
            "name": resource.display_name if resource.metadata else None,
            "tags": resource.search_tags if resource.metadata else None,
            "created_at": resource.created_at.isoformat() if resource.created_at else None,
        }

        result = self.client.table("system_resources").insert(data).execute()

        if result.data:
            return self._map_to_domain(result.data[0])

        return resource

    async def update(self, resource: SystemResource) -> SystemResource:
        """Update a resource."""
        data = {
            "category": resource.category.value if resource.category else None,
            "allowed_tiers": resource.access_control.allowed_tiers,
            "name": resource.display_name if resource.metadata else None,
            "tags": resource.search_tags if resource.metadata else None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        result = self.client.table("system_resources").update(data).eq(
            "id", resource.resource_id
        ).execute()

        if result.data:
            return self._map_to_domain(result.data[0])

        return resource

    async def delete(self, resource_id: str) -> bool:
        """Delete a resource."""
        result = self.client.table("system_resources").delete().eq(
            "id", resource_id
        ).execute()

        return len(result.data) > 0 if result.data else False

    async def count_by_type(self) -> dict:
        """Count resources by type."""
        result = self.client.table("system_resources").select("type").execute()

        counts = {}
        for row in (result.data or []):
            type_val = row.get("type", "unknown")
            counts[type_val] = counts.get(type_val, 0) + 1

        return counts

    async def count_by_tier(self) -> dict:
        """Count resources by tier requirement."""
        result = self.client.table("system_resources").select("allowed_tiers").execute()

        counts = {"free": 0, "starter": 0, "pro": 0}

        for row in (result.data or []):
            allowed_tiers = row.get("allowed_tiers", [])
            if "free" in allowed_tiers:
                counts["free"] += 1
            elif "starter" in allowed_tiers:
                counts["starter"] += 1
            elif "pro" in allowed_tiers:
                counts["pro"] += 1

        return counts

    def _map_to_domain(self, row: dict) -> SystemResource:
        """
        Map database row to domain model.

        Args:
            row: Database row

        Returns:
            SystemResource instance
        """
        resource_type = ResourceType(row["type"])
        category = ResourceCategory(row["category"]) if row.get("category") else None
        access_control = AccessControl(allowed_tiers=row.get("allowed_tiers", ["free"]))

        metadata = None
        if row.get("name") or row.get("tags"):
            metadata = ResourceMetadata(
                name=row.get("name"),
                tags=row.get("tags"),
            )

        created_at = None
        if row.get("created_at"):
            if isinstance(row["created_at"], str):
                created_at = datetime.fromisoformat(row["created_at"].replace('Z', '+00:00'))
            else:
                created_at = row["created_at"]

        updated_at = None
        if row.get("updated_at"):
            if isinstance(row["updated_at"], str):
                updated_at = datetime.fromisoformat(row["updated_at"].replace('Z', '+00:00'))
            else:
                updated_at = row["updated_at"]

        return SystemResource(
            resource_id=row["id"],
            resource_type=resource_type,
            url=row["url"],
            category=category,
            access_control=access_control,
            metadata=metadata,
            created_at=created_at,
            updated_at=updated_at,
        )
