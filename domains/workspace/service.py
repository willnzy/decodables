"""
Workspace Domain Service

Core business logic for Workspace domain.

@module domains.workspace.service
@version 2.0.0 (Phase 2: Multi-workspace support)
"""

from typing import Optional, List, Dict, Any
import logging

from .entities import Workspace
from .repository import IWorkspaceRepository

logger = logging.getLogger(__name__)

# Default workspace limits per tier
DEFAULT_MAX_WORKSPACES = 1  # Free/Starter: 1 workspace only
PRO_MAX_WORKSPACES = 10    # Pro: up to 10 workspaces


class WorkspaceService:
    """
    Workspace service.

    Phase 1: Default personal workspace management.
    Phase 2: Multi-workspace creation with tier-based quota.
    """

    def __init__(self, repository: IWorkspaceRepository, config_service=None):
        """
        Initialize service with repository.

        Args:
            repository: IWorkspaceRepository implementation
            config_service: Optional config service for quota settings
        """
        self._repo = repository
        self._config = config_service

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

    # ========== Phase 2: Multi-workspace ==========

    async def list_user_workspaces(self, user_id: str) -> List[Workspace]:
        """
        List all workspaces owned by user.

        Args:
            user_id: Clerk user_id

        Returns:
            List of Workspace entities (default first, then by created_at)
        """
        workspaces = await self._repo.get_by_owner(user_id)

        # If no workspaces exist, create default and return
        if not workspaces:
            default = await self.get_or_create_default(user_id)
            return [default]

        return workspaces

    async def create_workspace(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        user_tier: str = "t1",
    ) -> Workspace:
        """
        Create a new team workspace (Phase 2).

        Enforces tier-based quota:
        - t1 (Free) / t2 (Starter): max 1 workspace (default only)
        - t3 (Pro): max 10 workspaces

        Args:
            user_id: Clerk user_id
            name: Workspace name (1-100 chars)
            description: Optional description (max 500 chars)
            user_tier: User's subscription tier code

        Returns:
            Created Workspace entity

        Raises:
            ValueError: If validation fails or quota exceeded
        """
        # Validate name
        if not name or not name.strip():
            raise ValueError("Workspace name is required")
        name = name.strip()
        if len(name) > 100:
            raise ValueError("Workspace name cannot exceed 100 characters")

        # Validate description
        if description and len(description) > 500:
            raise ValueError("Description cannot exceed 500 characters")

        # Check quota
        # WS-04: TOCTOU note — Two concurrent create_workspace calls could both
        # pass this check. The DB doesn't enforce a per-user workspace count limit,
        # so we add a post-insert verification as a safety net.
        max_workspaces = await self._get_max_workspaces(user_tier)
        current_workspaces = await self._repo.get_by_owner(user_id)
        current_count = len(current_workspaces)

        if current_count >= max_workspaces:
            raise ValueError(
                f"Workspace limit reached ({current_count}/{max_workspaces}). "
                f"Upgrade to Pro for up to {PRO_MAX_WORKSPACES} workspaces."
            )

        # Create team workspace
        workspace = Workspace.create_team(
            owner_id=user_id,
            name=name,
            description=description,
        )
        created = await self._repo.create(workspace)

        # WS-04: Post-insert quota verification (defense against TOCTOU race)
        # If a concurrent request also created a workspace, check the total now.
        post_count = len(await self._repo.get_by_owner(user_id))
        if post_count > max_workspaces:
            # Over quota — rollback the workspace we just created
            logger.warning(
                f"[WorkspaceService] Quota exceeded after create (race detected): "
                f"user={user_id}, count={post_count}/{max_workspaces}"
            )
            await self._repo.delete(created.id)
            raise ValueError(
                f"Workspace limit reached ({max_workspaces}/{max_workspaces}). "
                f"Upgrade to Pro for up to {PRO_MAX_WORKSPACES} workspaces."
            )

        logger.info(
            f"[WorkspaceService] Created team workspace: "
            f"id={created.id}, user={user_id}, name={name}"
        )

        return created

    async def _get_max_workspaces(self, user_tier: str) -> int:
        """
        Get max workspaces allowed for tier.

        Args:
            user_tier: Tier code (t1/t2/t3/t4)

        Returns:
            Maximum number of workspaces allowed
        """
        # Try config service first
        if self._config:
            try:
                config_key = f"workspace.max_workspaces.{user_tier}"
                return await self._config.get_int(
                    config_key,
                    PRO_MAX_WORKSPACES if user_tier in ("t3", "t4") else DEFAULT_MAX_WORKSPACES
                )
            except Exception:
                pass

        # Fallback to hardcoded defaults
        if user_tier in ("t3", "t4"):
            return PRO_MAX_WORKSPACES
        return DEFAULT_MAX_WORKSPACES

    # ==========================================
    # Workspace Update / Delete / Stats
    # ==========================================

    async def update_workspace(
        self,
        workspace_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[Workspace]:
        """
        Update workspace name/description with ownership check.

        Args:
            workspace_id: Workspace UUID
            user_id: Clerk user_id (for ownership check)
            name: New workspace name
            description: New workspace description

        Returns:
            Updated Workspace entity or None

        Raises:
            PermissionError: If user is not the owner
            ValueError: If no valid fields to update
        """
        workspace = await self._repo.get_by_id(workspace_id)
        if not workspace:
            return None

        if workspace.owner_id != user_id:
            raise PermissionError("Not authorized to modify this workspace")

        update_data: Dict[str, Any] = {}
        if name is not None:
            update_data["name"] = name.strip()
        if description is not None:
            update_data["description"] = description.strip()

        if not update_data:
            return workspace

        updated = await self._repo.update_partial(workspace_id, update_data)
        if updated:
            logger.info(
                f"[WorkspaceService] Updated workspace: "
                f"id={workspace_id}, fields={list(update_data.keys())}"
            )
        return updated

    async def delete_workspace(
        self,
        workspace_id: str,
        user_id: str,
    ) -> bool:
        """
        Delete a workspace with ownership check.

        Args:
            workspace_id: Workspace UUID
            user_id: Clerk user_id (for ownership check)

        Returns:
            True if deleted

        Raises:
            PermissionError: If user is not the owner
            ValueError: If trying to delete default workspace or workspace not found
        """
        workspace = await self._repo.get_by_id(workspace_id)
        if not workspace:
            raise ValueError("Workspace not found")

        if workspace.owner_id != user_id:
            raise PermissionError("Not authorized to delete this workspace")

        if workspace.is_default:
            raise ValueError("Cannot delete default workspace")

        success = await self._repo.delete(workspace_id)
        if success:
            logger.info(
                f"[WorkspaceService] Deleted workspace: "
                f"id={workspace_id}, name={workspace.name}"
            )
        return success

    async def get_workspace_stats(
        self,
        workspace_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Get workspace statistics (tag/project/asset counts).

        Uses the repository's count methods for real data
        instead of hardcoded 0 values.

        Args:
            workspace_id: Workspace UUID
            user_id: Clerk user_id (for ownership check)

        Returns:
            Dict with workspace_id, tag_count, project_count, asset_count

        Raises:
            PermissionError: If user is not the owner
            ValueError: If workspace not found
        """
        workspace = await self._repo.get_by_id(workspace_id)
        if not workspace:
            raise ValueError("Workspace not found")

        if workspace.owner_id != user_id:
            raise PermissionError("Not authorized to access this workspace")

        # Count projects and assets owned by this user
        # We import here to avoid circular dependency
        from core.database import get_async_db_client
        client = await get_async_db_client()

        # Project count
        project_result = await client.table("projects").select(
            "id", count="exact"
        ).eq("user_id", user_id).eq("is_deleted", False).execute()
        project_count = project_result.count or 0

        # Asset count
        asset_result = await client.table("assets").select(
            "id", count="exact"
        ).eq("user_id", user_id).eq("is_deleted", False).execute()
        asset_count = asset_result.count or 0

        return {
            "workspace_id": workspace_id,
            "project_count": project_count,
            "asset_count": asset_count,
        }
