"""
Folder Domain Entities

Domain models for Folder domain.

@module domains.folder.entities
@version 1.0.0 (created for v3.33 Workspace + Tag Phase 2.6)
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class FolderColor(str, Enum):
    """
    Allowed folder colors (8 colors).

    Maps to Tailwind color classes on frontend:
    - slate -> bg-slate-100 text-slate-600
    - red -> bg-red-100 text-red-600
    - orange -> bg-orange-100 text-orange-600
    - amber -> bg-amber-100 text-amber-600
    - emerald -> bg-emerald-100 text-emerald-600
    - cyan -> bg-cyan-100 text-cyan-600
    - blue -> bg-blue-100 text-blue-600
    - violet -> bg-violet-100 text-violet-600
    """

    SLATE = "slate"
    RED = "red"
    ORANGE = "orange"
    AMBER = "amber"
    EMERALD = "emerald"
    CYAN = "cyan"
    BLUE = "blue"
    VIOLET = "violet"

    @classmethod
    def from_str(cls, value: str) -> "FolderColor":
        """Parse string to FolderColor, default to SLATE if invalid."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.SLATE


class FolderType(str, Enum):
    """
    Folder type to distinguish project vs asset folders.

    Folders are scoped to a specific type - a project folder
    can only contain projects, an asset folder can only contain assets.
    """

    PROJECT = "project"
    ASSET = "asset"

    @classmethod
    def from_str(cls, value: str) -> "FolderType":
        """Parse string to FolderType."""
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(f"Invalid folder type: {value}")


@dataclass
class Folder:
    """
    Folder entity.

    Folders belong to a Workspace and can contain either Projects or Assets
    based on their folder_type. Supports 8-color system for visual distinction.
    """

    id: Optional[str] = None
    workspace_id: str = ""
    folder_type: FolderType = FolderType.PROJECT
    name: str = ""
    color: FolderColor = FolderColor.SLATE
    sort_order: int = 0
    created_by: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Computed fields (not stored in DB)
    item_count: int = 0
    # v3.34: Sub-counts for filtering in Bought/Selling tabs
    bought_count: int = 0  # Projects with is_purchased=True
    selling_count: int = 0  # Projects with active marketplace listings
    # v3.37: Preview items for folder thumbnail grid (up to 4)
    preview_items: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "folder_type": self.folder_type.value if isinstance(self.folder_type, FolderType) else self.folder_type,
            "name": self.name,
            "color": self.color.value if isinstance(self.color, FolderColor) else self.color,
            "sort_order": self.sort_order,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "item_count": self.item_count,
            "bought_count": self.bought_count,
            "selling_count": self.selling_count,
            "preview_items": self.preview_items,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Folder":
        """Create entity from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

        # Parse folder_type
        folder_type_value = data.get("folder_type", "project")
        folder_type = FolderType.from_str(folder_type_value) if isinstance(folder_type_value, str) else folder_type_value

        # Parse color
        color_value = data.get("color", "slate")
        color = FolderColor.from_str(color_value) if isinstance(color_value, str) else color_value

        return cls(
            id=data.get("id"),
            workspace_id=data.get("workspace_id", ""),
            folder_type=folder_type,
            name=data.get("name", ""),
            color=color,
            sort_order=data.get("sort_order", 0),
            created_by=data.get("created_by", ""),
            created_at=created_at,
            updated_at=updated_at,
            item_count=data.get("item_count", 0),
            bought_count=data.get("bought_count", 0),
            selling_count=data.get("selling_count", 0),
        )

    @staticmethod
    def create_new(
        workspace_id: str,
        folder_type: FolderType,
        name: str,
        created_by: str,
        color: FolderColor = FolderColor.SLATE,
        sort_order: int = 0,
    ) -> "Folder":
        """
        Factory method to create a new folder.

        Args:
            workspace_id: UUID of the workspace this folder belongs to
            folder_type: Type of folder (project or asset)
            name: Folder name
            created_by: User ID of the creator
            color: Folder color (default: slate)
            sort_order: Sort order (default: 0)

        Returns:
            Folder entity ready for persistence
        """
        return Folder(
            workspace_id=workspace_id,
            folder_type=folder_type,
            name=name,
            color=color,
            sort_order=sort_order,
            created_by=created_by,
        )
