"""
Content Repository - Data access for system resources.

@module infrastructure.repositories.content_repository
@version 1.0.0

Purpose:
- Implements ISystemResourceRepository for content domain
- Returns SystemResource aggregate roots (not raw dicts)
- Used by user-facing API endpoints
"""

from typing import Optional, List
from datetime import datetime

from core.database import DatabaseClient
from core.database.retry import retry_on_network_error
from domains.content import (
    ISystemResourceRepository,
    SystemResource,
    ResourceType,
    ResourceCategory,
    ResourceMetadata,
    AccessControl,
)


class SupabaseContentRepository(ISystemResourceRepository):
    """
    Supabase implementation of ISystemResourceRepository.

    Returns SystemResource aggregate roots for use in domain services.
    """

    def __init__(self, db_client: DatabaseClient):
        """
        Initialize repository with database client.

        Args:
            db_client: AsyncClient instance (required)

        Raises:
            ValueError: If db_client is None
        """
        if db_client is None:
            raise ValueError("AsyncClient required for SupabaseContentRepository")
        self._client = db_client

    @property
    def client(self):
        """Get database client instance."""
        return self._client

    def _to_entity(self, data: dict) -> SystemResource:
        """
        Convert database record to SystemResource entity.

        Args:
            data: Database record dict

        Returns:
            SystemResource instance
        """
        # Parse resource type
        resource_type = ResourceType(data.get("resource_type", "sticker"))

        # Parse category (may be None)
        category = None
        if data.get("category"):
            try:
                category = ResourceCategory(data["category"])
            except ValueError:
                pass

        # Parse allowed_tiers
        allowed_tiers = data.get("allowed_tiers", ["t1"])
        if isinstance(allowed_tiers, str):
            allowed_tiers = [allowed_tiers]

        # Create access control
        try:
            access_control = AccessControl(allowed_tiers=allowed_tiers)
        except ValueError:
            # Fallback to free tier if invalid
            access_control = AccessControl(allowed_tiers=["t1"])

        # Create metadata
        metadata = ResourceMetadata(
            name=data.get("name") or data.get("display_name"),
            tags=data.get("tags") or [],
        )

        # Parse timestamps
        created_at = None
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(
                    data["created_at"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        updated_at = None
        if data.get("updated_at"):
            try:
                updated_at = datetime.fromisoformat(
                    data["updated_at"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        return SystemResource(
            resource_id=data.get("id") or data.get("resource_id"),
            resource_type=resource_type,
            url=data.get("url") or data.get("file_url") or "",
            category=category,
            access_control=access_control,
            metadata=metadata,
            created_at=created_at,
            updated_at=updated_at,
        )

    @retry_on_network_error()
    async def get_by_id(self, resource_id: str) -> Optional[SystemResource]:
        """
        Get resource by ID.

        Args:
            resource_id: Resource UUID

        Returns:
            SystemResource or None
        """
        result = await self.client.table("system_resources") \
            .select("*") \
            .eq("id", resource_id) \
            .eq("is_active", True) \
            .maybe_single() \
            .execute()

        if not result.data:
            return None

        return self._to_entity(result.data)

    @retry_on_network_error()
    async def get_all(
        self,
        resource_type: Optional[ResourceType] = None,
        category: Optional[ResourceCategory] = None,
        allowed_tiers_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[SystemResource]:
        """
        Get all resources with optional filtering.

        Args:
            resource_type: Filter by type
            category: Filter by category
            allowed_tiers_filter: Filter by tier
            limit: Max results
            offset: Results to skip

        Returns:
            List of SystemResource
        """
        query = self.client.table("system_resources") \
            .select("*") \
            .eq("is_active", True)

        if resource_type:
            query = query.eq("resource_type", resource_type.value)

        if category:
            query = query.eq("category", category.value)

        if allowed_tiers_filter:
            query = query.contains("allowed_tiers", [allowed_tiers_filter])

        # Sort by display_order first, then by created_at
        query = query \
            .order("display_order", desc=False) \
            .order("created_at", desc=True) \
            .range(offset, offset + limit - 1)

        result = await query.execute()

        if not result.data:
            return []

        return [self._to_entity(item) for item in result.data]

    @retry_on_network_error()
    async def create(self, resource: SystemResource) -> SystemResource:
        """
        Create a new resource.

        Args:
            resource: SystemResource to create

        Returns:
            Created SystemResource
        """
        data = {
            "id": resource.resource_id,
            "resource_type": resource.resource_type.value,
            "url": resource.url,
            "category": resource.category.value if resource.category else None,
            "allowed_tiers": resource.access_control.allowed_tiers,
            "name": resource.display_name,
            "tags": resource.search_tags,
            "is_active": True,
        }

        result = await self.client.table("system_resources") \
            .insert(data) \
            .execute()

        if result.data:
            return self._to_entity(result.data[0])

        return resource

    @retry_on_network_error()
    async def update(self, resource: SystemResource) -> SystemResource:
        """
        Update a resource.

        Args:
            resource: SystemResource to update

        Returns:
            Updated SystemResource
        """
        data = {
            "name": resource.display_name,
            "tags": resource.search_tags,
            "allowed_tiers": resource.access_control.allowed_tiers,
            "category": resource.category.value if resource.category else None,
            "updated_at": "now()",
        }

        result = await self.client.table("system_resources") \
            .update(data) \
            .eq("id", resource.resource_id) \
            .execute()

        if result.data:
            return self._to_entity(result.data[0])

        return resource

    @retry_on_network_error()
    async def delete(self, resource_id: str) -> bool:
        """
        Delete a resource (soft delete).

        Args:
            resource_id: Resource UUID

        Returns:
            True if deleted
        """
        result = await self.client.table("system_resources") \
            .update({"is_active": False, "updated_at": "now()"}) \
            .eq("id", resource_id) \
            .execute()

        return bool(result.data)

    @retry_on_network_error()
    async def count_by_type(self) -> dict:
        """
        Count resources by type.

        Returns:
            Dict of {type: count}
        """
        result = await self.client.table("system_resources") \
            .select("resource_type") \
            .eq("is_active", True) \
            .execute()

        counts = {}
        for item in result.data or []:
            rt = item.get("resource_type")
            counts[rt] = counts.get(rt, 0) + 1

        return counts

    @retry_on_network_error()
    async def count_by_tier(self) -> dict:
        """
        Count resources by tier requirement.

        Returns:
            Dict of {tier: count}
        """
        result = await self.client.table("system_resources") \
            .select("allowed_tiers") \
            .eq("is_active", True) \
            .execute()

        counts = {"t1": 0, "t2": 0, "t3": 0}
        for item in result.data or []:
            tiers = item.get("allowed_tiers", [])
            if isinstance(tiers, list):
                for tier in tiers:
                    if tier in counts:
                        counts[tier] += 1

        return counts
