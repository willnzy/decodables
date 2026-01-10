"""
Content Domain Value Objects - Immutable domain concepts.

@module domains.content.value_objects
@version 1.0.0
"""

from enum import Enum
from typing import List, Optional
from dataclasses import dataclass


class ResourceType(str, Enum):
    """System resource types."""
    PROJECT = "project"          # Project Template
    STICKER = "sticker"          # Sticker
    IMAGE = "image"              # Image Asset
    BACKGROUND = "background"    # Background Image
    FRAME = "frame"              # Frame/Decoration
    EMOJI = "emoji"              # Emoji
    FONT = "font"                # Font
    SHAPE = "shape"              # Shape/Graphic
    ICON = "icon"                # Icon
    PATTERN = "pattern"          # Pattern/Texture


class ResourceCategory(str, Enum):
    """Resource categories."""
    # Project categories
    STORY = "story"
    EDUCATIONAL = "educational"
    SEASONAL = "seasonal"
    BLANK = "blank"

    # Sticker categories
    ANIMALS = "animals"
    NATURE = "nature"
    PEOPLE = "people"
    FOOD = "food"
    OBJECTS = "objects"
    EMOTIONS = "emotions"
    EDUCATION = "education"
    HOLIDAY = "holiday"

    # Background/Pattern categories
    PATTERN = "pattern"

    # General
    POPULAR = "popular"
    NEW = "new"
    AI_GENERATED = "ai_generated"
    USER_UPLOAD = "user_upload"


# Resource type to categories mapping
TYPE_CATEGORIES = {
    ResourceType.PROJECT: [
        ResourceCategory.STORY,
        ResourceCategory.EDUCATIONAL,
        ResourceCategory.SEASONAL,
        ResourceCategory.BLANK,
    ],
    ResourceType.STICKER: [
        ResourceCategory.ANIMALS,
        ResourceCategory.NATURE,
        ResourceCategory.PEOPLE,
        ResourceCategory.FOOD,
        ResourceCategory.OBJECTS,
        ResourceCategory.EMOTIONS,
        ResourceCategory.EDUCATION,
        ResourceCategory.HOLIDAY,
    ],
    ResourceType.IMAGE: [
        ResourceCategory.ANIMALS,
        ResourceCategory.NATURE,
        ResourceCategory.PEOPLE,
        ResourceCategory.OBJECTS,
    ],
    ResourceType.BACKGROUND: [
        ResourceCategory.NATURE,
        ResourceCategory.PATTERN,
        ResourceCategory.SEASONAL,
    ],
}


@dataclass(frozen=True)
class ResourceId:
    """Resource identifier."""
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ResourceMetadata:
    """Resource metadata."""
    name: Optional[str] = None
    tags: Optional[List[str]] = None
    dimensions: Optional[dict] = None
    file_size: Optional[int] = None
    created_by: Optional[str] = None

    def __post_init__(self):
        # Validate tags is a list if provided
        if self.tags is not None and not isinstance(self.tags, list):
            object.__setattr__(self, 'tags', list(self.tags))


@dataclass(frozen=True)
class AccessControl:
    """Access control configuration for a resource."""
    allowed_tiers: List[str]

    def __post_init__(self):
        # Validate allowed_tiers
        valid_tiers = {"t1", "t2", "t3"}
        if not all(tier in valid_tiers for tier in self.allowed_tiers):
            raise ValueError(f"Invalid tiers. Must be subset of {valid_tiers}")

        # Ensure it's a list
        if not isinstance(self.allowed_tiers, list):
            object.__setattr__(self, 'allowed_tiers', list(self.allowed_tiers))

    def is_accessible_by_tier(self, user_tier: str) -> bool:
        """Check if a tier can access this resource."""
        return user_tier in self.allowed_tiers

    @classmethod
    def free_tier(cls):
        """Create free tier access."""
        return cls(allowed_tiers=["t1"])

    @classmethod
    def starter_plus(cls):
        """Create starter+ access."""
        return cls(allowed_tiers=["t2", "t3"])

    @classmethod
    def pro_only(cls):
        """Create pro-only access."""
        return cls(allowed_tiers=["t3"])
