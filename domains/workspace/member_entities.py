"""
Workspace Member Domain Entities

Domain models for workspace membership and invitations.

@module domains.workspace.member_entities
@version 1.0.0 (created for v3.33 Phase 5)
"""

from typing import Optional
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field


@dataclass
class WorkspaceMember:
    """
    Workspace member entity.

    Represents a user's membership in a workspace with a role.
    """

    id: Optional[str] = None
    workspace_id: str = ""
    user_id: str = ""
    role: str = "member"  # 'owner' | 'member'
    invited_by: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            "role": self.role,
            "invited_by": self.invited_by,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkspaceMember":
        """Create entity from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

        return cls(
            id=data.get("id"),
            workspace_id=data.get("workspace_id", ""),
            user_id=data.get("user_id", ""),
            role=data.get("role", "member"),
            invited_by=data.get("invited_by"),
            is_active=data.get("is_active", True),
            created_at=created_at,
            updated_at=updated_at,
        )

    @staticmethod
    def create_owner(workspace_id: str, user_id: str) -> "WorkspaceMember":
        """Factory: Create owner membership."""
        return WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role="owner",
            is_active=True,
        )

    @staticmethod
    def create_member(
        workspace_id: str,
        user_id: str,
        invited_by: str,
    ) -> "WorkspaceMember":
        """Factory: Create member membership."""
        return WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role="member",
            invited_by=invited_by,
            is_active=True,
        )


@dataclass
class WorkspaceInvitation:
    """
    Workspace invitation entity.

    Represents a pending invitation to join a workspace.
    """

    id: Optional[str] = None
    workspace_id: str = ""
    invited_email: str = ""
    invited_by: str = ""
    role: str = "member"
    status: str = "pending"  # 'pending' | 'accepted' | 'declined' | 'expired'
    expires_at: Optional[datetime] = None
    accepted_by: Optional[str] = None
    accepted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "invited_email": self.invited_email,
            "invited_by": self.invited_by,
            "role": self.role,
            "status": self.status,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "accepted_by": self.accepted_by,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkspaceInvitation":
        """Create entity from dictionary."""
        def parse_dt(val):
            if isinstance(val, str):
                return datetime.fromisoformat(val.replace("Z", "+00:00"))
            return val

        return cls(
            id=data.get("id"),
            workspace_id=data.get("workspace_id", ""),
            invited_email=data.get("invited_email", ""),
            invited_by=data.get("invited_by", ""),
            role=data.get("role", "member"),
            status=data.get("status", "pending"),
            expires_at=parse_dt(data.get("expires_at")),
            accepted_by=data.get("accepted_by"),
            accepted_at=parse_dt(data.get("accepted_at")),
            created_at=parse_dt(data.get("created_at")),
            updated_at=parse_dt(data.get("updated_at")),
        )

    @staticmethod
    def create(
        workspace_id: str,
        invited_email: str,
        invited_by: str,
        role: str = "member",
    ) -> "WorkspaceInvitation":
        """Factory: Create a new invitation (expires in 7 days)."""
        return WorkspaceInvitation(
            workspace_id=workspace_id,
            invited_email=invited_email.lower().strip(),
            invited_by=invited_by,
            role=role,
            status="pending",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

    @property
    def is_expired(self) -> bool:
        """Check if invitation has expired."""
        if not self.expires_at:
            return False
        now = datetime.now(timezone.utc)
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return now > expires

    @property
    def is_pending(self) -> bool:
        """Check if invitation is still pending and valid."""
        return self.status == "pending" and not self.is_expired
