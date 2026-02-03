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
            # 使用 .limit(1) 替代 .single()
            # .single() 在有多行时抛出 PGRST116（与 0 行同一错误码），
            # 导致代码误判为"不存在"而触发重复创建的恶性循环
            result = await self.client.table("workspaces")\
                .select("*")\
                .eq("owner_id", owner_id)\
                .eq("is_default", True)\
                .eq("is_active", True)\
                .limit(1)\
                .execute()

            if result.data:
                return Workspace.from_dict(result.data[0])
            return None

        except Exception as e:
            logger.error(f"[WorkspaceRepository] get_default_by_owner failed: {e}")
            raise

    @retry_on_network_error()
    async def get_or_create_default_atomic(self, owner_id: str) -> Workspace:
        """
        Atomically get or create user's default workspace via RPC.

        Uses PostgreSQL function with ON CONFLICT to eliminate race conditions.
        Falls back to application-level get_or_create if RPC not available.

        Args:
            owner_id: User ID (UUID string)

        Returns:
            Default Workspace entity (existing or newly created)
        """
        try:
            result = await self.client.rpc(
                "get_or_create_default_workspace",
                {"p_owner_id": owner_id},
            ).execute()

            if result.data:
                return Workspace.from_dict(result.data)

            # Fallback: should not happen, but defensive
            logger.warning(
                f"[WorkspaceRepository] RPC returned empty, "
                f"falling back to query for user={owner_id}"
            )
            return await self.get_default_by_owner(owner_id)

        except Exception as e:
            # RPC not found (not deployed yet) - graceful fallback
            if "PGRST202" in str(e):
                logger.warning(
                    "[WorkspaceRepository] RPC get_or_create_default_workspace "
                    "not found, falling back to non-atomic method"
                )
                return await self._fallback_get_or_create_default(owner_id)
            logger.error(
                f"[WorkspaceRepository] get_or_create_default_atomic failed: {e}"
            )
            raise

    async def _fallback_get_or_create_default(self, owner_id: str) -> Workspace:
        """
        Non-atomic fallback for get_or_create when RPC is not available.

        This is only used when the RPC function hasn't been deployed yet.
        """
        workspace = await self.get_default_by_owner(owner_id)
        if workspace:
            return workspace

        # Create new default workspace
        new_workspace = Workspace.create_default(owner_id=owner_id)
        return await self.create(new_workspace)

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

    @retry_on_network_error()
    async def update_partial(self, workspace_id: str, data: dict) -> Optional[Workspace]:
        """Partially update a workspace."""
        try:
            if not workspace_id:
                raise ValueError("Workspace ID required for update")

            # Only allow safe fields to be updated
            allowed_fields = {"name", "description"}
            update_data = {k: v for k, v in data.items() if k in allowed_fields}

            if not update_data:
                # No valid fields to update, fetch and return current
                return await self.get_by_id(workspace_id)

            result = await self.client.table("workspaces")\
                .update(update_data)\
                .eq("id", workspace_id)\
                .eq("is_active", True)\
                .execute()

            if result.data:
                logger.info(
                    f"[WorkspaceRepository] Updated workspace: "
                    f"id={workspace_id}, fields={list(update_data.keys())}"
                )
                return Workspace.from_dict(result.data[0])

            return None

        except Exception as e:
            logger.error(f"[WorkspaceRepository] update_partial failed: {e}")
            raise

    @retry_on_network_error()
    async def delete(self, workspace_id: str) -> bool:
        """Soft delete a workspace (set is_active=False)."""
        try:
            if not workspace_id:
                raise ValueError("Workspace ID required for delete")

            result = await self.client.table("workspaces")\
                .update({"is_active": False})\
                .eq("id", workspace_id)\
                .execute()

            success = bool(result.data)
            if success:
                logger.info(f"[WorkspaceRepository] Soft deleted workspace: id={workspace_id}")

            return success

        except Exception as e:
            logger.error(f"[WorkspaceRepository] delete failed: {e}")
            raise
