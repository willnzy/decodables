"""
Tag Domain

User-level tagging system for organizing projects and assets.

@module domains.tag
@version 1.0.0 (created for v3.33 Workspace + Tag Phase 1)
"""

from .entities import (
    Tag,
    TagColor,
    TagSource,
    TagGroupPreset,
    ProjectTag,
    UserAssetTag,
)
from .repository import (
    ITagRepository,
    IProjectTagRepository,
    IAssetTagRepository,
)
from .service import (
    TagService,
    ProjectTagService,
    AssetTagService,
)

__all__ = [
    # Entities
    "Tag",
    "TagColor",
    "TagSource",
    "TagGroupPreset",
    "ProjectTag",
    "UserAssetTag",
    # Repository interfaces
    "ITagRepository",
    "IProjectTagRepository",
    "IAssetTagRepository",
    # Services
    "TagService",
    "ProjectTagService",
    "AssetTagService",
]
