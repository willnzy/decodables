"""
SystemResource Aggregate Root - Official content resources.

@module domains.content.aggregates.system_resource
@version 1.0.0
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime, timezone

from ..value_objects import (
    ResourceId,
    ResourceType,
    ResourceCategory,
    ResourceMetadata,
    AccessControl,
)
from ..exceptions import InvalidResourceDataException


@dataclass
class SystemResource:
    """
    SystemResource aggregate root.

    Represents official platform resources (stickers, backgrounds, templates, etc.)
    provided by the system for users to use in their projects.

    Business rules:
    - Projects are Pro-only regardless of allowed_tiers
    - Resources have tier-based access control
    - Resources can be locked for users without proper tier
    """

    resource_id: str
    resource_type: ResourceType
    url: str
    access_control: AccessControl
    category: Optional[ResourceCategory] = None
    metadata: Optional[ResourceMetadata] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate resource on creation."""
        if not self.url or not self.url.strip():
            raise InvalidResourceDataException("url", "URL is required")

    @classmethod
    def create_new(
        cls,
        resource_type: ResourceType,
        url: str,
        category: Optional[ResourceCategory] = None,
        allowed_tiers: Optional[List[str]] = None,
        name: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> "SystemResource":
        """
        Create a new system resource.

        Args:
            resource_type: Type of resource
            url: Resource URL
            category: Resource category
            allowed_tiers: Tiers that can access (defaults to ["free"])
            name: Display name
            tags: Search tags

        Returns:
            New SystemResource instance
        """
        import uuid

        access_control = AccessControl(allowed_tiers=allowed_tiers or ["free"])
        metadata = ResourceMetadata(name=name, tags=tags) if (name or tags) else None

        return cls(
            resource_id=str(uuid.uuid4()),
            resource_type=resource_type,
            url=url,
            category=category,
            access_control=access_control,
            metadata=metadata,
            created_at=datetime.now(timezone.utc),
        )

    def is_accessible_by(self, user_tier: str) -> bool:
        """
        Check if user can access this resource.

        Business rule: Projects are Pro-only regardless of allowed_tiers.

        Args:
            user_tier: User's subscription tier

        Returns:
            True if accessible
        """
        # PRD v3.2: Projects are Pro-only
        if self.resource_type == ResourceType.PROJECT:
            return user_tier == "pro"

        # Other resources follow allowed_tiers
        return self.access_control.is_accessible_by_tier(user_tier)

    def update_metadata(
        self,
        name: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ):
        """
        Update resource metadata.

        Args:
            name: New name
            tags: New tags
        """
        if name or tags:
            current_name = self.metadata.name if self.metadata else None
            current_tags = self.metadata.tags if self.metadata else None

            self.metadata = ResourceMetadata(
                name=name if name is not None else current_name,
                tags=tags if tags is not None else current_tags,
            )

        self.updated_at = datetime.now(timezone.utc)

    def update_access_control(self, allowed_tiers: List[str]):
        """
        Update access control.

        Args:
            allowed_tiers: New allowed tiers
        """
        self.access_control = AccessControl(allowed_tiers=allowed_tiers)
        self.updated_at = datetime.now(timezone.utc)

    @property
    def display_name(self) -> str:
        """Get display name."""
        if self.metadata and self.metadata.name:
            return self.metadata.name
        return self.resource_id

    @property
    def search_tags(self) -> List[str]:
        """Get search tags."""
        if self.metadata and self.metadata.tags:
            return self.metadata.tags
        return []
