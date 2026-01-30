"""
Workspace Member Repository Interface

Defines the contract for member and invitation data access.

@module domains.workspace.member_repository
@version 1.0.0 (created for v3.33 Phase 5)
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from .member_entities import WorkspaceMember, WorkspaceInvitation


class IMemberRepository(ABC):
    """Abstract repository interface for workspace membership."""

    # ========== Members ==========

    @abstractmethod
    async def get_member(self, workspace_id: str, user_id: str) -> Optional[WorkspaceMember]:
        """Get a specific member of a workspace."""
        pass

    @abstractmethod
    async def list_members(self, workspace_id: str) -> List[WorkspaceMember]:
        """List all active members of a workspace."""
        pass

    @abstractmethod
    async def create_member(self, member: WorkspaceMember) -> WorkspaceMember:
        """Create a new membership record."""
        pass

    @abstractmethod
    async def update_member_role(
        self, member_id: str, role: str, workspace_id: Optional[str] = None,
    ) -> Optional[WorkspaceMember]:
        """Update a member's role."""
        pass

    @abstractmethod
    async def remove_member(
        self, member_id: str, workspace_id: Optional[str] = None,
    ) -> bool:
        """Soft delete a member (set is_active=False)."""
        pass

    @abstractmethod
    async def count_members(self, workspace_id: str) -> int:
        """Count active members of a workspace."""
        pass

    # ========== Invitations ==========

    @abstractmethod
    async def get_invitation(self, invitation_id: str) -> Optional[WorkspaceInvitation]:
        """Get an invitation by ID."""
        pass

    @abstractmethod
    async def get_pending_invitation(
        self, workspace_id: str, email: str
    ) -> Optional[WorkspaceInvitation]:
        """Get a pending invitation for an email in a workspace."""
        pass

    @abstractmethod
    async def list_workspace_invitations(
        self, workspace_id: str, status: Optional[str] = None
    ) -> List[WorkspaceInvitation]:
        """List invitations for a workspace."""
        pass

    @abstractmethod
    async def list_user_invitations(self, email: str) -> List[WorkspaceInvitation]:
        """List all pending invitations for a user email."""
        pass

    @abstractmethod
    async def create_invitation(self, invitation: WorkspaceInvitation) -> WorkspaceInvitation:
        """Create a new invitation."""
        pass

    @abstractmethod
    async def update_invitation_status(
        self, invitation_id: str, status: str, accepted_by: Optional[str] = None
    ) -> Optional[WorkspaceInvitation]:
        """Update invitation status."""
        pass
