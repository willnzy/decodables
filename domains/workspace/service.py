"""
Workspace Domain Service

Core business logic for Workspace domain.

@module domains.workspace.service
@version 1.0.0 (created for v3.33 Workspace + Tag Phase 1)
"""

from typing import Optional
import logging

from .entities import Workspace
from .repository import IWorkspaceRepository

logger = logging.getLogger(__name__)


class WorkspaceService:
    """
    Workspace service.

    Phase 1: Only manages default personal workspaces.
    Users don't see workspace UI, but data is organized by workspace.
    """

    def __init__(self, repository: IWorkspaceRepository):
        """
        Initialize service with repository.

        Args:
            repository: IWorkspaceRepository implementation
        """
        self._repo = repository

    async def get_or_create_default(self, user_id: str) -> Workspace:
        """
        Get user's default workspace, create if not exists.

        This is the primary method for Phase 1 - ensures every user
        has exactly one default workspace.

        Args:
            user_id: Clerk user_id

        Returns:
            User's default Workspace (existing or newly created)
        """
        # Try to get existing default workspace
        workspace = await self._repo.get_default_by_owner(user_id)
        if workspace:
            logger.debug(f"[WorkspaceService] Found existing workspace for user {user_id}")
            return workspace

        # Create new default workspace
        new_workspace = Workspace.create_default(owner_id=user_id)
        created = await self._repo.create(new_workspace)

        logger.info(
            f"[WorkspaceService] Created default workspace: "
            f"id={created.id}, user={user_id}"
        )

        return created

    async def get_user_workspace_id(self, user_id: str) -> str:
        """
        Get user's workspace_id (convenience method).

        Phase 1: Users have exactly one workspace.

        Args:
            user_id: Clerk user_id

        Returns:
            Workspace UUID string
        """
        workspace = await self.get_or_create_default(user_id)
        return workspace.id

    async def get_by_id(self, workspace_id: str) -> Optional[Workspace]:
        """
        Get workspace by ID.

        Args:
            workspace_id: Workspace UUID

        Returns:
            Workspace entity or None if not found
        """
        return await self._repo.get_by_id(workspace_id)

    async def validate_ownership(self, workspace_id: str, user_id: str) -> bool:
        """
        Validate that user owns the workspace.

        Phase 1: Simple ownership check.
        Phase 2+: May include member/role checks.

        Args:
            workspace_id: Workspace UUID
            user_id: Clerk user_id

        Returns:
            True if user owns the workspace
        """
        workspace = await self._repo.get_by_id(workspace_id)
        if not workspace:
            return False
        return workspace.owner_id == user_id

    async def ensure_workspace_for_user(self, user_id: str) -> str:
        """
        Ensure user has a workspace and return its ID.

        Alias for get_user_workspace_id() with more explicit intent.
        Called during user registration to ensure workspace exists.

        Args:
            user_id: Clerk user_id

        Returns:
            Workspace UUID string
        """
        return await self.get_user_workspace_id(user_id)
