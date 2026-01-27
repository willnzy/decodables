"""
Tag Domain Entities

Domain models for Tag domain.

@module domains.tag.entities
@version 1.0.0 (created for v3.33 Workspace + Tag Phase 1)
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class TagColor(str, Enum):
    """
    Allowed tag colors.

    Maps to Tailwind color classes on frontend:
    - gray -> bg-slate-100 text-slate-700
    - red -> bg-red-100 text-red-700
    - etc.
    """

    GRAY = "gray"
    RED = "red"
    ORANGE = "orange"
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"
    PURPLE = "purple"
    PINK = "pink"

    @classmethod
    def from_str(cls, value: str) -> "TagColor":
        """Parse string to TagColor, default to GRAY if invalid."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.GRAY


class TagSource(str, Enum):
    """Source of tag assignment."""

    MANUAL = "manual"
    AI_RECOMMENDED = "ai_recommended"


@dataclass
class Tag:
    """
    User-level tag entity.

    Tags belong to a Workspace and can be applied to Projects and Assets.
    """

    id: Optional[str] = None
    workspace_id: str = ""
    name: str = ""
    color: TagColor = TagColor.GRAY
    icon: Optional[str] = None
    group_name: Optional[str] = None
    sort_order: int = 0
    created_by: str = ""
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Computed field (not stored in DB)
    usage_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "name": self.name,
            "color": self.color.value if isinstance(self.color, TagColor) else self.color,
            "icon": self.icon,
            "group_name": self.group_name,
            "sort_order": self.sort_order,
            "created_by": self.created_by,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "usage_count": self.usage_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Tag":
        """Create entity from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

        color_value = data.get("color", "gray")
        color = TagColor.from_str(color_value) if isinstance(color_value, str) else color_value

        return cls(
            id=data.get("id"),
            workspace_id=data.get("workspace_id", ""),
            name=data.get("name", ""),
            color=color,
            icon=data.get("icon"),
            group_name=data.get("group_name"),
            sort_order=data.get("sort_order", 0),
            created_by=data.get("created_by", ""),
            is_active=data.get("is_active", True),
            created_at=created_at,
            updated_at=updated_at,
            usage_count=data.get("usage_count", 0),
        )


@dataclass
class TagGroupPreset:
    """
    System-level tag group preset.

    Templates for creating tags when a new workspace is created.
    """

    id: Optional[str] = None
    group_name: str = ""
    display_name: str = ""
    description: Optional[str] = None
    icon: Optional[str] = None
    preset_tags: List[Dict[str, Any]] = field(default_factory=list)
    is_default: bool = False
    sort_order: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "group_name": self.group_name,
            "display_name": self.display_name,
            "description": self.description,
            "icon": self.icon,
            "preset_tags": self.preset_tags,
            "is_default": self.is_default,
            "sort_order": self.sort_order,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TagGroupPreset":
        """Create entity from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

        return cls(
            id=data.get("id"),
            group_name=data.get("group_name", ""),
            display_name=data.get("display_name", ""),
            description=data.get("description"),
            icon=data.get("icon"),
            preset_tags=data.get("preset_tags", []),
            is_default=data.get("is_default", False),
            sort_order=data.get("sort_order", 0),
            is_active=data.get("is_active", True),
            created_at=created_at,
            updated_at=updated_at,
        )


@dataclass
class ProjectTag:
    """
    Project-Tag association entity.

    Represents the many-to-many relationship between projects and tags.
    """

    project_id: str = ""
    tag_id: str = ""
    added_by: str = ""
    added_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "project_id": self.project_id,
            "tag_id": self.tag_id,
            "added_by": self.added_by,
            "added_at": self.added_at.isoformat() if self.added_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectTag":
        """Create entity from dictionary."""
        added_at = data.get("added_at")
        if isinstance(added_at, str):
            added_at = datetime.fromisoformat(added_at.replace("Z", "+00:00"))

        return cls(
            project_id=data.get("project_id", ""),
            tag_id=data.get("tag_id", ""),
            added_by=data.get("added_by", ""),
            added_at=added_at,
        )


@dataclass
class UserAssetTag:
    """
    Asset-Tag association entity.

    Represents the many-to-many relationship between assets and tags.
    Includes source field to distinguish manual vs AI-recommended tags.
    """

    asset_id: str = ""
    tag_id: str = ""
    added_by: str = ""
    added_at: Optional[datetime] = None
    source: TagSource = TagSource.MANUAL

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "asset_id": self.asset_id,
            "tag_id": self.tag_id,
            "added_by": self.added_by,
            "added_at": self.added_at.isoformat() if self.added_at else None,
            "source": self.source.value if isinstance(self.source, TagSource) else self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserAssetTag":
        """Create entity from dictionary."""
        added_at = data.get("added_at")
        if isinstance(added_at, str):
            added_at = datetime.fromisoformat(added_at.replace("Z", "+00:00"))

        source_value = data.get("source", "manual")
        try:
            source = TagSource(source_value)
        except ValueError:
            source = TagSource.MANUAL

        return cls(
            asset_id=data.get("asset_id", ""),
            tag_id=data.get("tag_id", ""),
            added_by=data.get("added_by", ""),
            added_at=added_at,
            source=source,
        )
