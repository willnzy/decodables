"""
Content Domain Repository Interfaces.

@module domains.content.repository
@version 1.0.0
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from .aggregates.system_resource import SystemResource
from .value_objects import ResourceType, ResourceCategory


class ISystemResourceRepository(ABC):
    """Repository interface for SystemResource aggregate."""

    @abstractmethod
    async def get_by_id(self, resource_id: str) -> Optional[SystemResource]:
        """
        Get resource by ID.

        Args:
            resource_id: Resource ID

        Returns:
            SystemResource or None
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def create(self, resource: SystemResource) -> SystemResource:
        """
        Create a new resource.

        Args:
            resource: SystemResource to create

        Returns:
            Created SystemResource
        """
        pass

    @abstractmethod
    async def update(self, resource: SystemResource) -> SystemResource:
        """
        Update a resource.

        Args:
            resource: SystemResource to update

        Returns:
            Updated SystemResource
        """
        pass

    @abstractmethod
    async def delete(self, resource_id: str) -> bool:
        """
        Delete a resource.

        Args:
            resource_id: Resource ID

        Returns:
            True if deleted
        """
        pass

    @abstractmethod
    async def count_by_type(self) -> dict:
        """
        Count resources by type.

        Returns:
            Dict of {type: count}
        """
        pass

    @abstractmethod
    async def count_by_tier(self) -> dict:
        """
        Count resources by tier requirement.

        Returns:
            Dict of {tier: count}
        """
        pass
