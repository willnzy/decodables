"""
Creation Value Objects - Immutable domain primitives.

@module domains.creation.value_objects
@version 1.0.0
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid


class ProjectStatus(str, Enum):
    """Project lifecycle status."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

    @property
    def is_editable(self) -> bool:
        """Check if project can be edited."""
        return self in (ProjectStatus.DRAFT, ProjectStatus.ACTIVE)

    @property
    def is_visible(self) -> bool:
        """Check if project is visible in lists."""
        return self in (ProjectStatus.DRAFT, ProjectStatus.ACTIVE)


class AssetType(str, Enum):
    """Type of generated asset."""
    IMAGE = "image"
    TEXT = "text"
    STICKER = "sticker"
    TEMPLATE = "template"
    BACKGROUND = "background"
    ELEMENT = "element"


@dataclass(frozen=True)
class ProjectId:
    """
    Project identifier value object.

    Uses UUID for unique identification.
    """
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("Project ID cannot be empty")

    @classmethod
    def generate(cls) -> "ProjectId":
        """Generate a new project ID."""
        return cls(str(uuid.uuid4()))

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other) -> bool:
        if isinstance(other, ProjectId):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return False

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True)
class AssetId:
    """
    Asset identifier value object.
    """
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("Asset ID cannot be empty")

    @classmethod
    def generate(cls) -> "AssetId":
        """Generate a new asset ID."""
        return cls(str(uuid.uuid4()))

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other) -> bool:
        if isinstance(other, AssetId):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return False

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True)
class CanvasSize:
    """
    Canvas dimensions value object.

    Constraints:
    - Width and height must be positive integers
    - Maximum 4096px per dimension (browser canvas rendering limit,
      also enforced by CHECK constraint in DB schema)
    """
    width: int
    height: int

    def __post_init__(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Canvas dimensions must be positive")
        if self.width > 4096 or self.height > 4096:
            raise ValueError("Canvas dimensions cannot exceed 4096px")

    @property
    def aspect_ratio(self) -> float:
        """Get aspect ratio (width/height)."""
        return self.width / self.height

    @property
    def is_square(self) -> bool:
        """Check if canvas is square."""
        return self.width == self.height

    @property
    def is_portrait(self) -> bool:
        """Check if canvas is portrait orientation."""
        return self.height > self.width

    @property
    def is_landscape(self) -> bool:
        """Check if canvas is landscape orientation."""
        return self.width > self.height

    def to_string(self) -> str:
        """Get string representation."""
        return f"{self.width}x{self.height}"

    @classmethod
    def from_string(cls, size_str: str) -> "CanvasSize":
        """
        Create from string like '1080x1080'.

        Args:
            size_str: Size string in format 'WIDTHxHEIGHT'

        Returns:
            CanvasSize instance

        Raises:
            ValueError: If format is invalid or values are not numeric
        """
        parts = size_str.split("x")
        if len(parts) != 2:
            raise ValueError(f"Invalid size format: {size_str}")
        try:
            width = int(parts[0])
            height = int(parts[1])
        except (ValueError, TypeError):
            raise ValueError(f"Invalid size values (must be integers): {size_str}")
        return cls(width, height)

    # Common presets
    @classmethod
    def instagram_square(cls) -> "CanvasSize":
        return cls(1080, 1080)

    @classmethod
    def instagram_story(cls) -> "CanvasSize":
        return cls(1080, 1920)

    @classmethod
    def a4_portrait(cls) -> "CanvasSize":
        return cls(2480, 3508)  # 300 DPI


@dataclass(frozen=True)
class ProjectMetadata:
    """
    Project metadata value object (immutable).

    WS-4 (1B#10): Made frozen=True for proper DDD value object semantics.
    Updates create new instances via replace() method.
    """
    title: str
    description: Optional[str] = None
    tags: tuple = ()  # Use tuple for immutability (frozen dataclass)
    thumbnail_url: Optional[str] = None
    is_public: bool = False
    is_template: bool = False
    template_category: Optional[str] = None
    view_count: int = 0
    like_count: int = 0

    def replace(self, **kwargs) -> "ProjectMetadata":
        """
        Create a new ProjectMetadata with updated fields.

        Returns:
            New ProjectMetadata instance with specified fields updated.
        """
        from dataclasses import asdict
        current = asdict(self)
        current.update(kwargs)
        return ProjectMetadata(**current)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "tags": list(self.tags),
            "thumbnail_url": self.thumbnail_url,
            "is_public": self.is_public,
            "is_template": self.is_template,
            "template_category": self.template_category,
            "view_count": self.view_count,
            "like_count": self.like_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectMetadata":
        """Create from dictionary."""
        tags = data.get("tags", [])
        return cls(
            title=data.get("title", "Untitled"),
            description=data.get("description"),
            tags=tuple(tags) if isinstance(tags, list) else tags,
            thumbnail_url=data.get("thumbnail_url"),
            is_public=data.get("is_public", False),
            is_template=data.get("is_template", False),
            template_category=data.get("template_category"),
            view_count=data.get("view_count", 0),
            like_count=data.get("like_count", 0),
        )


@dataclass(frozen=True)
class AssetMetadata:
    """
    Asset metadata value object.
    """
    asset_type: AssetType
    file_url: str
    file_size: int
    mime_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    generation_prompt: Optional[str] = None
    generation_params: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "asset_type": self.asset_type.value,
            "file_url": self.file_url,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "width": self.width,
            "height": self.height,
            "generation_prompt": self.generation_prompt,
            "generation_params": self.generation_params,
        }
