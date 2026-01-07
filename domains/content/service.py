"""
Content Domain Service - Orchestrates content operations.

@module domains.content.service
@version 1.0.0
"""

from typing import Optional, List, Dict, Any

from .aggregates.system_resource import SystemResource
from .repository import ISystemResourceRepository
from .value_objects import ResourceType, ResourceCategory, TYPE_CATEGORIES
from .exceptions import (
    ResourceNotFoundException,
    InvalidResourceTypeException,
    InvalidCategoryException,
)


class ContentService:
    """
    Domain service for content operations.

    This service:
    - Manages system resource lifecycle
    - Enforces access rules
    - Provides resource discovery
    """

    def __init__(self, repository: ISystemResourceRepository):
        """
        Initialize content service with repository.

        Args:
            repository: SystemResource repository implementation
        """
        self._repository = repository

    async def get_resource(self, resource_id: str) -> Optional[SystemResource]:
        """
        Get resource by ID.

        Args:
            resource_id: Resource ID

        Returns:
            SystemResource or None
        """
        return await self._repository.get_by_id(resource_id)

    async def get_resource_or_raise(self, resource_id: str) -> SystemResource:
        """
        Get resource or raise exception.

        Args:
            resource_id: Resource ID

        Returns:
            SystemResource

        Raises:
            ResourceNotFoundException: If not found
        """
        resource = await self._repository.get_by_id(resource_id)
        if not resource:
            raise ResourceNotFoundException(resource_id)
        return resource

    async def get_resources(
        self,
        resource_type: Optional[ResourceType] = None,
        category: Optional[ResourceCategory] = None,
        allowed_tiers_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[SystemResource]:
        """
        Get resources with filtering.

        Args:
            resource_type: Filter by type
            category: Filter by category
            allowed_tiers_filter: Filter by tier
            limit: Max results
            offset: Results to skip

        Returns:
            List of SystemResource
        """
        return await self._repository.get_all(
            resource_type=resource_type,
            category=category,
            allowed_tiers_filter=allowed_tiers_filter,
            limit=limit,
            offset=offset,
        )

    async def get_resources_with_access(
        self,
        user_tier: str,
        resource_type: Optional[ResourceType] = None,
        category: Optional[ResourceCategory] = None,
        allowed_tiers_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        include_locked: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get resources with access information for user.

        Args:
            user_tier: User's subscription tier
            resource_type: Filter by type
            category: Filter by category
            allowed_tiers_filter: Filter by tier
            limit: Max results
            offset: Results to skip
            include_locked: Include locked resources

        Returns:
            List of resource dicts with is_accessible/is_locked flags
        """
        resources = await self.get_resources(
            resource_type=resource_type,
            category=category,
            allowed_tiers_filter=allowed_tiers_filter,
            limit=limit,
            offset=offset,
        )

        result = []
        for resource in resources:
            is_accessible = resource.is_accessible_by(user_tier)

            # Skip locked items if not including them
            if not is_accessible and not include_locked:
                continue

            result.append({
                "id": resource.resource_id,
                "type": resource.resource_type.value,
                "url": resource.url,
                "category": resource.category.value if resource.category else None,
                "allowed_tiers": resource.access_control.allowed_tiers,
                "name": resource.display_name,
                "tags": resource.search_tags,
                "is_accessible": is_accessible,
                "is_locked": not is_accessible,
                "created_at": resource.created_at.isoformat() if resource.created_at else None,
            })

        return result

    async def get_stickers(
        self,
        user_tier: str,
        category: Optional[ResourceCategory] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Get stickers for editor.

        Args:
            user_tier: User's tier
            category: Filter by category
            limit: Max results
            offset: Results to skip

        Returns:
            Dict with items, total, page info
        """
        items = await self.get_resources_with_access(
            user_tier=user_tier,
            resource_type=ResourceType.STICKER,
            category=category,
            limit=limit,
            offset=offset,
            include_locked=True,
        )

        return {
            "items": items,
            "total": len(items),
            "page": (offset // limit) + 1 if limit > 0 else 1,
            "limit": limit,
        }

    async def get_backgrounds(
        self,
        user_tier: str,
        category: Optional[ResourceCategory] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Get backgrounds.

        Args:
            user_tier: User's tier
            category: Filter by category
            limit: Max results
            offset: Results to skip

        Returns:
            Dict with items, total, page info
        """
        items = await self.get_resources_with_access(
            user_tier=user_tier,
            resource_type=ResourceType.BACKGROUND,
            category=category,
            limit=limit,
            offset=offset,
            include_locked=True,
        )

        return {
            "items": items,
            "total": len(items),
            "page": (offset // limit) + 1 if limit > 0 else 1,
            "limit": limit,
        }

    async def get_projects(
        self,
        user_tier: str,
        category: Optional[ResourceCategory] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Get project templates.

        Args:
            user_tier: User's tier
            category: Filter by category
            limit: Max results
            offset: Results to skip

        Returns:
            Dict with items, total, page info
        """
        items = await self.get_resources_with_access(
            user_tier=user_tier,
            resource_type=ResourceType.PROJECT,
            category=category,
            limit=limit,
            offset=offset,
            include_locked=True,
        )

        return {
            "items": items,
            "total": len(items),
            "page": (offset // limit) + 1 if limit > 0 else 1,
            "limit": limit,
        }

    def get_categories_for_type(
        self,
        resource_type: ResourceType
    ) -> List[Dict[str, str]]:
        """
        Get available categories for a resource type.

        Args:
            resource_type: Resource type

        Returns:
            List of category info
        """
        categories = TYPE_CATEGORIES.get(resource_type, [])

        return [
            {
                "id": cat.value,
                "name": cat.value.replace("_", " ").title(),
            }
            for cat in categories
        ]

    async def get_resource_stats(self) -> Dict[str, Any]:
        """
        Get resource statistics.

        Returns:
            Stats by type and tier
        """
        type_counts = await self._repository.count_by_type()
        tier_counts = await self._repository.count_by_tier()

        total = sum(type_counts.values())

        return {
            "total": total,
            "by_type": type_counts,
            "by_tier": tier_counts,
        }

    # ==========================================
    # Admin Methods
    # ==========================================

    async def create_resource(
        self,
        resource_type: ResourceType,
        url: str,
        category: Optional[ResourceCategory] = None,
        allowed_tiers: Optional[List[str]] = None,
        name: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> SystemResource:
        """
        Create a new system resource (admin only).

        Args:
            resource_type: Resource type
            url: Resource URL
            category: Category
            allowed_tiers: Access tiers
            name: Display name
            tags: Search tags

        Returns:
            Created SystemResource
        """
        resource = SystemResource.create_new(
            resource_type=resource_type,
            url=url,
            category=category,
            allowed_tiers=allowed_tiers,
            name=name,
            tags=tags,
        )

        return await self._repository.create(resource)

    async def update_resource(
        self,
        resource_id: str,
        name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        allowed_tiers: Optional[List[str]] = None,
    ) -> SystemResource:
        """
        Update a system resource (admin only).

        Args:
            resource_id: Resource ID
            name: New name
            tags: New tags
            allowed_tiers: New allowed tiers

        Returns:
            Updated SystemResource
        """
        resource = await self.get_resource_or_raise(resource_id)

        if name or tags:
            resource.update_metadata(name=name, tags=tags)

        if allowed_tiers:
            resource.update_access_control(allowed_tiers)

        return await self._repository.update(resource)

    async def delete_resource(self, resource_id: str) -> bool:
        """
        Delete a system resource (admin only).

        Args:
            resource_id: Resource ID

        Returns:
            True if deleted
        """
        return await self._repository.delete(resource_id)
