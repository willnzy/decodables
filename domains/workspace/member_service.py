"""
Workspace Member Service

Business logic for workspace membership and invitations.

@module domains.workspace.member_service
@version 1.0.0 (created for v3.33 Phase 5)
"""

from typing import Optional, List
import logging
import re

from .member_entities import WorkspaceMember, WorkspaceInvitation
from .member_repository import IMemberRepository
from .repository import IWorkspaceRepository

logger = logging.getLogger(__name__)

# Maximum members per workspace (configurable via system_configs later)
MAX_MEMBERS_PER_WORKSPACE = 20

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class MemberService:
    """
    Workspace member management service.

    Handles:
    - Member listing and role management
    - Invitation creation, acceptance, and decline
    - Permission checks (owner vs member)
    """

    def __init__(
        self,
        member_repo: IMemberRepository,
        workspace_repo: IWorkspaceRepository,
    ):
        self._member_repo = member_repo
        self._workspace_repo = workspace_repo

    # ========== Members ==========

    async def check_access(self, workspace_id: str, user_id: str) -> bool:
        """
        WS-06: Check if user has access to workspace (owner or active member).

        Unlike _verify_membership, this returns bool instead of raising.

        Args:
            workspace_id: Workspace UUID
            user_id: User to check access for

        Returns:
            True if user is owner or active member, False otherwise
        """
        try:
            await self._verify_membership(workspace_id, user_id)
            return True
        except ValueError:
            return False

    async def list_members(self, workspace_id: str, user_id: str) -> List[WorkspaceMember]:
        """
        List all active members of a workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: Requesting user's ID (must be a member)

        Returns:
            List of WorkspaceMember entities

        Raises:
            ValueError: If user is not a member
        """
        await self._verify_membership(workspace_id, user_id)
        return await self._member_repo.list_members(workspace_id)

    async def invite_member(
        self,
        workspace_id: str,
        inviter_id: str,
        email: str,
        role: str = "member",
    ) -> WorkspaceInvitation:
        """
        Invite a user to a workspace by email.

        Args:
            workspace_id: Workspace UUID
            inviter_id: User ID of the person inviting
            email: Email address to invite
            role: Role to assign (currently only 'member')

        Returns:
            Created WorkspaceInvitation

        Raises:
            ValueError: If validation fails
            PermissionError: If inviter is not the workspace owner
        """
        # Validate email
        email = email.lower().strip()
        if not EMAIL_REGEX.match(email):
            raise ValueError("Invalid email address")

        # Only owners can invite
        await self._verify_ownership(workspace_id, inviter_id)

        # Check workspace exists
        workspace = await self._workspace_repo.get_by_id(workspace_id)
        if not workspace:
            raise ValueError("Workspace not found")

        # Check member count limit
        member_count = await self._member_repo.count_members(workspace_id)
        if member_count >= MAX_MEMBERS_PER_WORKSPACE:
            raise ValueError(
                f"Workspace has reached the maximum of {MAX_MEMBERS_PER_WORKSPACE} members"
            )

        # Check for existing pending invitation
        existing = await self._member_repo.get_pending_invitation(workspace_id, email)
        if existing and existing.is_pending:
            raise ValueError(f"A pending invitation already exists for {email}")

        # Create invitation
        invitation = WorkspaceInvitation.create(
            workspace_id=workspace_id,
            invited_email=email,
            invited_by=inviter_id,
            role=role,
        )
        created = await self._member_repo.create_invitation(invitation)

        logger.info(
            f"[MemberService] Invitation created: workspace={workspace_id}, "
            f"email={email}, invited_by={inviter_id}"
        )

        return created

    async def accept_invitation(
        self,
        invitation_id: str,
        user_id: str,
        user_email: str,
    ) -> WorkspaceMember:
        """
        Accept a workspace invitation.

        Args:
            invitation_id: Invitation UUID
            user_id: Accepting user's ID
            user_email: Accepting user's email (must match invitation)

        Returns:
            Created WorkspaceMember

        Raises:
            ValueError: If invitation is invalid or expired
        """
        invitation = await self._member_repo.get_invitation(invitation_id)
        if not invitation:
            raise ValueError("Invitation not found")

        if invitation.status != "pending":
            raise ValueError(f"Invitation is already {invitation.status}")

        if invitation.is_expired:
            # Auto-expire
            await self._member_repo.update_invitation_status(invitation_id, "expired")
            raise ValueError("Invitation has expired")

        if invitation.invited_email != user_email.lower().strip():
            raise ValueError("This invitation is for a different email address")

        # Check if already a member
        existing = await self._member_repo.get_member(invitation.workspace_id, user_id)
        if existing and existing.is_active:
            # Update invitation status anyway
            await self._member_repo.update_invitation_status(
                invitation_id, "accepted", accepted_by=user_id
            )
            raise ValueError("You are already a member of this workspace")

        # Create member record
        member = WorkspaceMember.create_member(
            workspace_id=invitation.workspace_id,
            user_id=user_id,
            invited_by=invitation.invited_by,
        )
        created = await self._member_repo.create_member(member)

        # Update invitation status
        await self._member_repo.update_invitation_status(
            invitation_id, "accepted", accepted_by=user_id
        )

        logger.info(
            f"[MemberService] Invitation accepted: workspace={invitation.workspace_id}, "
            f"user={user_id}"
        )

        return created

    async def decline_invitation(self, invitation_id: str, user_email: str) -> None:
        """
        Decline a workspace invitation.

        Args:
            invitation_id: Invitation UUID
            user_email: Declining user's email

        Raises:
            ValueError: If invitation is invalid
        """
        invitation = await self._member_repo.get_invitation(invitation_id)
        if not invitation:
            raise ValueError("Invitation not found")

        if invitation.status != "pending":
            raise ValueError(f"Invitation is already {invitation.status}")

        if invitation.invited_email != user_email.lower().strip():
            raise ValueError("This invitation is for a different email address")

        await self._member_repo.update_invitation_status(invitation_id, "declined")

        logger.info(
            f"[MemberService] Invitation declined: id={invitation_id}, email={user_email}"
        )

    async def remove_member(
        self,
        workspace_id: str,
        remover_id: str,
        target_member_id: str,
    ) -> None:
        """
        Remove a member from a workspace.

        Args:
            workspace_id: Workspace UUID
            remover_id: User ID performing the removal (must be owner)
            target_member_id: Member record ID to remove

        Raises:
            PermissionError: If remover is not the owner
            ValueError: If trying to remove the owner
        """
        # Only owners can remove members
        await self._verify_ownership(workspace_id, remover_id)

        # Get the target member
        members = await self._member_repo.list_members(workspace_id)
        target = next((m for m in members if m.id == target_member_id), None)
        if not target:
            raise ValueError("Member not found")

        # Cannot remove the owner
        if target.role == "owner":
            raise ValueError("Cannot remove the workspace owner")

        await self._member_repo.remove_member(target_member_id, workspace_id=workspace_id)

        logger.info(
            f"[MemberService] Member removed: workspace={workspace_id}, "
            f"member={target_member_id}, removed_by={remover_id}"
        )

    async def update_member_role(
        self,
        workspace_id: str,
        updater_id: str,
        target_member_id: str,
        new_role: str,
    ) -> WorkspaceMember:
        """
        Update a member's role (currently limited to owner operations).

        Args:
            workspace_id: Workspace UUID
            updater_id: User ID performing the update (must be owner)
            target_member_id: Member record ID to update
            new_role: New role ('member' only for now)

        Returns:
            Updated WorkspaceMember

        Raises:
            PermissionError: If updater is not the owner
            ValueError: If invalid role
        """
        if new_role not in ("member",):
            raise ValueError("Invalid role. Allowed roles: member")

        await self._verify_ownership(workspace_id, updater_id)

        updated = await self._member_repo.update_member_role(
            target_member_id, new_role, workspace_id=workspace_id,
        )
        if not updated:
            raise ValueError("Member not found")

        return updated

    async def get_user_invitations(self, user_email: str) -> List[WorkspaceInvitation]:
        """
        Get all pending invitations for a user.

        Args:
            user_email: User's email address

        Returns:
            List of pending WorkspaceInvitation entities
        """
        invitations = await self._member_repo.list_user_invitations(
            user_email.lower().strip()
        )
        # Filter out expired ones
        return [inv for inv in invitations if inv.is_pending]

    async def list_workspace_invitations(
        self, workspace_id: str, user_id: str
    ) -> List[WorkspaceInvitation]:
        """
        List invitations for a workspace (owner only).

        Args:
            workspace_id: Workspace UUID
            user_id: Requesting user (must be owner)

        Returns:
            List of WorkspaceInvitation entities
        """
        await self._verify_ownership(workspace_id, user_id)
        return await self._member_repo.list_workspace_invitations(workspace_id)

    # ========== Permission Helpers ==========

    async def _verify_membership(self, workspace_id: str, user_id: str) -> WorkspaceMember:
        """Verify user is a member of the workspace."""
        # Check if user is the workspace owner
        workspace = await self._workspace_repo.get_by_id(workspace_id)
        if workspace and workspace.owner_id == user_id:
            # Owner is always a member
            return WorkspaceMember(
                workspace_id=workspace_id,
                user_id=user_id,
                role="owner",
                is_active=True,
            )

        member = await self._member_repo.get_member(workspace_id, user_id)
        if not member or not member.is_active:
            raise ValueError("You are not a member of this workspace")
        return member

    async def _verify_ownership(self, workspace_id: str, user_id: str) -> None:
        """Verify user is the owner of the workspace."""
        workspace = await self._workspace_repo.get_by_id(workspace_id)
        if not workspace:
            raise ValueError("Workspace not found")
        if workspace.owner_id != user_id:
            raise PermissionError("Only the workspace owner can perform this action")
