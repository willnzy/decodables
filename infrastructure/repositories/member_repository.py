"""
Workspace Member Repository Implementation - Supabase data access.

@module infrastructure.repositories.member_repository
@version 1.0.0 (created for v3.33 Phase 5)

Implements IMemberRepository using Supabase PostgreSQL.
"""

from typing import Optional, List
from datetime import datetime, timezone
import logging

from domains.workspace.member_repository import IMemberRepository
from domains.workspace.member_entities import WorkspaceMember, WorkspaceInvitation
from core.database.retry import retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseMemberRepository(IMemberRepository):
    """Supabase implementation of workspace member repository."""

    def __init__(self, client):
        if client is None:
            raise ValueError("AsyncClient required for SupabaseMemberRepository")
        self._client = client

    @property
    def client(self):
        return self._client

    # ========== Members ==========

    @retry_on_network_error()
    async def get_member(self, workspace_id: str, user_id: str) -> Optional[WorkspaceMember]:
        """Get a specific member of a workspace."""
        try:
            result = await self.client.table("workspace_members")\
                .select("*")\
                .eq("workspace_id", workspace_id)\
                .eq("user_id", user_id)\
                .eq("is_active", True)\
                .single()\
                .execute()

            if result.data:
                return WorkspaceMember.from_dict(result.data)
            return None
        except Exception as e:
            if "No rows found" in str(e) or "PGRST116" in str(e):
                return None
            logger.error(f"[MemberRepository] get_member failed: {e}")
            raise

    @retry_on_network_error()
    async def list_members(self, workspace_id: str) -> List[WorkspaceMember]:
        """List all active members of a workspace."""
        try:
            result = await self.client.table("workspace_members")\
                .select("*")\
                .eq("workspace_id", workspace_id)\
                .eq("is_active", True)\
                .order("created_at")\
                .execute()

            return [WorkspaceMember.from_dict(row) for row in (result.data or [])]
        except Exception as e:
            logger.error(f"[MemberRepository] list_members failed: {e}")
            raise

    @retry_on_network_error()
    async def create_member(self, member: WorkspaceMember) -> WorkspaceMember:
        """Create a new membership record."""
        try:
            data = {
                "workspace_id": member.workspace_id,
                "user_id": member.user_id,
                "role": member.role,
                "invited_by": member.invited_by,
                "is_active": True,
            }

            result = await self.client.table("workspace_members")\
                .insert(data)\
                .execute()

            if result.data:
                created = WorkspaceMember.from_dict(result.data[0])
                logger.info(
                    f"[MemberRepository] Created member: workspace={member.workspace_id}, "
                    f"user={member.user_id}, role={member.role}"
                )
                return created
            return member
        except Exception as e:
            logger.error(f"[MemberRepository] create_member failed: {e}")
            raise

    @retry_on_network_error()
    async def update_member_role(self, member_id: str, role: str) -> Optional[WorkspaceMember]:
        """Update a member's role."""
        try:
            result = await self.client.table("workspace_members")\
                .update({"role": role})\
                .eq("id", member_id)\
                .eq("is_active", True)\
                .execute()

            if result.data:
                return WorkspaceMember.from_dict(result.data[0])
            return None
        except Exception as e:
            logger.error(f"[MemberRepository] update_member_role failed: {e}")
            raise

    @retry_on_network_error()
    async def remove_member(self, member_id: str) -> bool:
        """Soft delete a member."""
        try:
            result = await self.client.table("workspace_members")\
                .update({"is_active": False})\
                .eq("id", member_id)\
                .execute()

            success = bool(result.data)
            if success:
                logger.info(f"[MemberRepository] Removed member: id={member_id}")
            return success
        except Exception as e:
            logger.error(f"[MemberRepository] remove_member failed: {e}")
            raise

    @retry_on_network_error()
    async def count_members(self, workspace_id: str) -> int:
        """Count active members of a workspace."""
        try:
            result = await self.client.table("workspace_members")\
                .select("id", count="exact")\
                .eq("workspace_id", workspace_id)\
                .eq("is_active", True)\
                .execute()

            return result.count or 0
        except Exception as e:
            logger.error(f"[MemberRepository] count_members failed: {e}")
            raise

    # ========== Invitations ==========

    @retry_on_network_error()
    async def get_invitation(self, invitation_id: str) -> Optional[WorkspaceInvitation]:
        """Get an invitation by ID."""
        try:
            result = await self.client.table("workspace_invitations")\
                .select("*")\
                .eq("id", invitation_id)\
                .single()\
                .execute()

            if result.data:
                return WorkspaceInvitation.from_dict(result.data)
            return None
        except Exception as e:
            if "No rows found" in str(e) or "PGRST116" in str(e):
                return None
            logger.error(f"[MemberRepository] get_invitation failed: {e}")
            raise

    @retry_on_network_error()
    async def get_pending_invitation(
        self, workspace_id: str, email: str
    ) -> Optional[WorkspaceInvitation]:
        """Get a pending invitation for an email in a workspace."""
        try:
            result = await self.client.table("workspace_invitations")\
                .select("*")\
                .eq("workspace_id", workspace_id)\
                .eq("invited_email", email.lower().strip())\
                .eq("status", "pending")\
                .single()\
                .execute()

            if result.data:
                return WorkspaceInvitation.from_dict(result.data)
            return None
        except Exception as e:
            if "No rows found" in str(e) or "PGRST116" in str(e):
                return None
            logger.error(f"[MemberRepository] get_pending_invitation failed: {e}")
            raise

    @retry_on_network_error()
    async def list_workspace_invitations(
        self, workspace_id: str, status: Optional[str] = None
    ) -> List[WorkspaceInvitation]:
        """List invitations for a workspace."""
        try:
            query = self.client.table("workspace_invitations")\
                .select("*")\
                .eq("workspace_id", workspace_id)\
                .order("created_at", desc=True)

            if status:
                query = query.eq("status", status)

            result = await query.execute()
            return [WorkspaceInvitation.from_dict(row) for row in (result.data or [])]
        except Exception as e:
            logger.error(f"[MemberRepository] list_workspace_invitations failed: {e}")
            raise

    @retry_on_network_error()
    async def list_user_invitations(self, email: str) -> List[WorkspaceInvitation]:
        """List all pending invitations for a user email."""
        try:
            result = await self.client.table("workspace_invitations")\
                .select("*")\
                .eq("invited_email", email.lower().strip())\
                .eq("status", "pending")\
                .order("created_at", desc=True)\
                .execute()

            return [WorkspaceInvitation.from_dict(row) for row in (result.data or [])]
        except Exception as e:
            logger.error(f"[MemberRepository] list_user_invitations failed: {e}")
            raise

    @retry_on_network_error()
    async def create_invitation(self, invitation: WorkspaceInvitation) -> WorkspaceInvitation:
        """Create a new invitation."""
        try:
            data = {
                "workspace_id": invitation.workspace_id,
                "invited_email": invitation.invited_email,
                "invited_by": invitation.invited_by,
                "role": invitation.role,
                "status": "pending",
                "expires_at": invitation.expires_at.isoformat() if invitation.expires_at else None,
            }

            result = await self.client.table("workspace_invitations")\
                .insert(data)\
                .execute()

            if result.data:
                created = WorkspaceInvitation.from_dict(result.data[0])
                logger.info(
                    f"[MemberRepository] Created invitation: workspace={invitation.workspace_id}, "
                    f"email={invitation.invited_email}"
                )
                return created
            return invitation
        except Exception as e:
            logger.error(f"[MemberRepository] create_invitation failed: {e}")
            raise

    @retry_on_network_error()
    async def update_invitation_status(
        self, invitation_id: str, status: str, accepted_by: Optional[str] = None
    ) -> Optional[WorkspaceInvitation]:
        """Update invitation status."""
        try:
            update_data: dict = {"status": status}
            if accepted_by:
                update_data["accepted_by"] = accepted_by
                update_data["accepted_at"] = datetime.now(timezone.utc).isoformat()

            result = await self.client.table("workspace_invitations")\
                .update(update_data)\
                .eq("id", invitation_id)\
                .execute()

            if result.data:
                return WorkspaceInvitation.from_dict(result.data[0])
            return None
        except Exception as e:
            logger.error(f"[MemberRepository] update_invitation_status failed: {e}")
            raise
