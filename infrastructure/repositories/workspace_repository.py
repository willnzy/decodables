"""
Workspace Repository Implementation - Supabase data access.

@module infrastructure.repositories.workspace_repository
@version 1.0.0 (created for v3.33 Workspace + Tag Phase 1)

Implements IWorkspaceRepository using Supabase PostgreSQL.
"""

from typing import Optional, List
import logging

from domains.workspace.repository import IWorkspaceRepository
from domains.workspace.entities import Workspace
from core.database.retry import retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseWorkspaceRepository(IWorkspaceRepository):
    """
    Supabase implementation of Workspace repository.

    Phase 1: Minimal implementation for default workspace management.
    """

    def __init__(self, client):
        """
        Initialize repository with AsyncClient.

        Args:
            client: AsyncClient instance (required)

        Raises:
            ValueError: If client is None
        """
        if client is None:
            raise ValueError("AsyncClient required for SupabaseWorkspaceRepository")
        self._client = client

    @property
    def client(self):
        """Get AsyncClient instance."""
        return self._client

    @retry_on_network_error()
    async def get_by_id(self, workspace_id: str) -> Optional[Workspace]:
        """Get workspace by ID."""
        try:
            result = await self.client.table("workspaces")\
                .select("*")\
                .eq("id", workspace_id)\
                .eq("is_active", True)\
                .single()\
                .execute()

            if result.data:
                return Workspace.from_dict(result.data)
            return None

        except Exception as e:
            # single() raises when no row found
            if "No rows found" in str(e) or "PGRST116" in str(e):
                return None
            logger.error(f"[WorkspaceRepository] get_by_id failed: {e}")
            raise

    @retry_on_network_error()
    async def get_default_by_owner(self, owner_id: str) -> Optional[Workspace]:
        """Get user's default workspace."""
        try:
            result = await self.client.table("workspaces")\
                .select("*")\
                .eq("owner_id", owner_id)\
                .eq("is_default", True)\
                .eq("is_active", True)\
                .single()\
                .execute()

            if result.data:
                return Workspace.from_dict(result.data)
            return None

        except Exception as e:
            # single() raises when no row found
            if "No rows found" in str(e) or "PGRST116" in str(e):
                return None
            logger.error(f"[WorkspaceRepository] get_default_by_owner failed: {e}")
            raise

    @retry_on_network_error()
    async def get_by_owner(self, owner_id: str) -> List[Workspace]:
        """Get all workspaces for a user."""
        try:
            result = await self.client.table("workspaces")\
                .select("*")\
                .eq("owner_id", owner_id)\
                .eq("is_active", True)\
                .order("created_at")\
                .execute()

            return [Workspace.from_dict(row) for row in (result.data or [])]

        except Exception as e:
            logger.error(f"[WorkspaceRepository] get_by_owner failed: {e}")
            raise

    @retry_on_network_error()
    async def create(self, workspace: Workspace) -> Workspace:
        """Create a new workspace."""
        try:
            data = {
                "name": workspace.name,
                "description": workspace.description,
                "owner_id": workspace.owner_id,
                "is_default": workspace.is_default,
                "is_personal": workspace.is_personal,
                "is_active": workspace.is_active,
            }

            result = await self.client.table("workspaces")\
                .insert(data)\
                .execute()

            if result.data:
                created = Workspace.from_dict(result.data[0])
                logger.info(
                    f"[WorkspaceRepository] Created workspace: "
                    f"id={created.id}, owner={workspace.owner_id}"
                )
                return created

            return workspace

        except Exception as e:
            logger.error(f"[WorkspaceRepository] create failed: {e}")
            raise

    @retry_on_network_error()
    async def update(self, workspace: Workspace) -> Workspace:
        """Update an existing workspace."""
        try:
            if not workspace.id:
                raise ValueError("Workspace ID required for update")

            data = {
                "name": workspace.name,
                "description": workspace.description,
                "is_default": workspace.is_default,
                "is_personal": workspace.is_personal,
                "is_active": workspace.is_active,
            }

            result = await self.client.table("workspaces")\
                .update(data)\
                .eq("id", workspace.id)\
                .execute()

            if result.data:
                return Workspace.from_dict(result.data[0])

            return workspace

        except Exception as e:
            logger.error(f"[WorkspaceRepository] update failed: {e}")
            raise

    @retry_on_network_error()
    async def exists(self, workspace_id: str) -> bool:
        """Check if a workspace exists."""
        try:
            result = await self.client.table("workspaces")\
                .select("id")\
                .eq("id", workspace_id)\
                .eq("is_active", True)\
                .execute()

            return bool(result.data)

        except Exception as e:
            logger.error(f"[WorkspaceRepository] exists failed: {e}")
            raise
