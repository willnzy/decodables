"""
Workspace Domain Entities

Domain models for Workspace domain.

@module domains.workspace.entities
@version 1.0.0 (created for v3.33 Workspace + Tag Phase 1)
"""

from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass


@dataclass
class Workspace:
    """
    Workspace entity.

    Phase 1: Only Personal Workspace supported.
    Each user has exactly one default workspace.
    """

    id: Optional[str] = None
    name: str = "My Workspace"
    description: Optional[str] = None
    owner_id: str = ""
    is_default: bool = True
    is_personal: bool = True
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "owner_id": self.owner_id,
            "is_default": self.is_default,
            "is_personal": self.is_personal,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workspace":
        """Create entity from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

        return cls(
            id=data.get("id"),
            name=data.get("name", "My Workspace"),
            description=data.get("description"),
            owner_id=data.get("owner_id", ""),
            is_default=data.get("is_default", True),
            is_personal=data.get("is_personal", True),
            is_active=data.get("is_active", True),
            created_at=created_at,
            updated_at=updated_at,
        )

    @staticmethod
    def create_default(owner_id: str, name: str = "My Workspace") -> "Workspace":
        """
        Factory method to create a default personal workspace.

        Args:
            owner_id: Clerk user_id of the workspace owner
            name: Workspace name (default: "My Workspace")

        Returns:
            Workspace entity ready for persistence
        """
        return Workspace(
            name=name,
            owner_id=owner_id,
            is_default=True,
            is_personal=True,
            is_active=True,
        )

    @staticmethod
    def create_team(owner_id: str, name: str, description: Optional[str] = None) -> "Workspace":
        """
        Factory method to create a non-default team workspace.

        Phase 2+: Pro users can create additional workspaces for collaboration.

        Args:
            owner_id: Clerk user_id of the workspace owner
            name: Workspace name (required)
            description: Optional description

        Returns:
            Workspace entity ready for persistence
        """
        return Workspace(
            name=name,
            description=description,
            owner_id=owner_id,
            is_default=False,
            is_personal=False,
            is_active=True,
        )
