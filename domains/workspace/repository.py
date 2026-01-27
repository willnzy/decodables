"""
Workspace Repository Interface

Defines the contract for Workspace data access.

@module domains.workspace.repository
@version 1.0.0 (created for v3.33 Workspace + Tag Phase 1)
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from .entities import Workspace


class IWorkspaceRepository(ABC):
    """
    Abstract repository interface for Workspace domain.

    Phase 1: Minimal interface for default workspace management.
    """

    @abstractmethod
    async def get_by_id(self, workspace_id: str) -> Optional[Workspace]:
        """
        Get workspace by ID.

        Args:
            workspace_id: Workspace UUID

        Returns:
            Workspace entity or None if not found
        """
        pass

    @abstractmethod
    async def get_default_by_owner(self, owner_id: str) -> Optional[Workspace]:
        """
        Get user's default workspace.

        Args:
            owner_id: Clerk user_id

        Returns:
            Default Workspace entity or None if not found
        """
        pass

    @abstractmethod
    async def get_by_owner(self, owner_id: str) -> List[Workspace]:
        """
        Get all workspaces for a user.

        Phase 1: Returns single default workspace.
        Phase 2+: May return multiple workspaces.

        Args:
            owner_id: Clerk user_id

        Returns:
            List of Workspace entities
        """
        pass

    @abstractmethod
    async def create(self, workspace: Workspace) -> Workspace:
        """
        Create a new workspace.

        Args:
            workspace: Workspace entity to create

        Returns:
            Created Workspace with ID populated
        """
        pass

    @abstractmethod
    async def update(self, workspace: Workspace) -> Workspace:
        """
        Update an existing workspace.

        Args:
            workspace: Workspace entity with updated fields

        Returns:
            Updated Workspace entity
        """
        pass

    @abstractmethod
    async def exists(self, workspace_id: str) -> bool:
        """
        Check if a workspace exists.

        Args:
            workspace_id: Workspace UUID

        Returns:
            True if workspace exists
        """
        pass

    @abstractmethod
    async def update_partial(self, workspace_id: str, data: dict) -> Optional[Workspace]:
        """
        Partially update a workspace.

        Args:
            workspace_id: Workspace UUID
            data: Dictionary of fields to update

        Returns:
            Updated Workspace entity or None if not found
        """
        pass

    @abstractmethod
    async def delete(self, workspace_id: str) -> bool:
        """
        Soft delete a workspace (set is_active=False).

        Args:
            workspace_id: Workspace UUID

        Returns:
            True if deleted successfully
        """
        pass
