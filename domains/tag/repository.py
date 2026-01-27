"""
Tag Repository Interface

Defines the contract for Tag data access.

@module domains.tag.repository
@version 1.0.0 (created for v3.33 Workspace + Tag Phase 1)
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from .entities import Tag, TagGroupPreset, ProjectTag, UserAssetTag


class ITagRepository(ABC):
    """
    Abstract repository interface for Tag domain.

    Handles tag CRUD and tag-preset operations.
    """

    # ==================== Tag Operations ====================

    @abstractmethod
    async def get_by_id(self, tag_id: str) -> Optional[Tag]:
        """Get tag by ID."""
        pass

    @abstractmethod
    async def get_by_workspace(
        self,
        workspace_id: str,
        group_name: Optional[str] = None,
        include_inactive: bool = False
    ) -> List[Tag]:
        """
        Get all tags for a workspace.

        Args:
            workspace_id: Workspace UUID
            group_name: Optional filter by group
            include_inactive: Include soft-deleted tags

        Returns:
            List of Tag entities
        """
        pass

    @abstractmethod
    async def get_by_name(self, workspace_id: str, name: str) -> Optional[Tag]:
        """
        Get tag by name within a workspace.

        Args:
            workspace_id: Workspace UUID
            name: Tag name (case-insensitive match)

        Returns:
            Tag entity or None if not found
        """
        pass

    @abstractmethod
    async def create(self, tag: Tag) -> Tag:
        """
        Create a new tag.

        Args:
            tag: Tag entity to create

        Returns:
            Created Tag with ID populated

        Raises:
            ValueError: If tag name already exists in workspace
        """
        pass

    @abstractmethod
    async def create_batch(self, tags: List[Tag]) -> List[Tag]:
        """
        Create multiple tags at once.

        Args:
            tags: List of Tag entities to create

        Returns:
            List of created Tags with IDs populated
        """
        pass

    @abstractmethod
    async def update(self, tag: Tag) -> Tag:
        """Update an existing tag."""
        pass

    @abstractmethod
    async def delete(self, tag_id: str) -> bool:
        """
        Soft delete a tag (set is_active = False).

        Also removes all project_tags and user_asset_tags associations.

        Args:
            tag_id: Tag UUID

        Returns:
            True if deleted successfully
        """
        pass

    @abstractmethod
    async def count_by_workspace(self, workspace_id: str) -> int:
        """Count active tags in a workspace."""
        pass

    # ==================== Preset Operations ====================

    @abstractmethod
    async def get_all_presets(self) -> List[TagGroupPreset]:
        """Get all active tag group presets."""
        pass

    @abstractmethod
    async def get_default_presets(self) -> List[TagGroupPreset]:
        """Get presets marked as default (auto-apply to new workspaces)."""
        pass


class IProjectTagRepository(ABC):
    """
    Abstract repository interface for Project-Tag associations.
    """

    @abstractmethod
    async def get_tags_for_project(self, project_id: str) -> List[Tag]:
        """Get all tags for a project."""
        pass

    @abstractmethod
    async def get_projects_by_tags(
        self,
        tag_ids: List[str],
        match_mode: str = "any",
        offset: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get projects that have specified tags.

        Args:
            tag_ids: List of tag UUIDs
            match_mode: "any" (OR) or "all" (AND)
            offset: Pagination offset
            limit: Page size

        Returns:
            Dict with project_ids, total, has_more
        """
        pass

    @abstractmethod
    async def add_tag(self, project_id: str, tag_id: str, user_id: str) -> ProjectTag:
        """Add a tag to a project."""
        pass

    @abstractmethod
    async def add_tags(
        self,
        project_id: str,
        tag_ids: List[str],
        user_id: str
    ) -> List[ProjectTag]:
        """Add multiple tags to a project."""
        pass

    @abstractmethod
    async def remove_tag(self, project_id: str, tag_id: str) -> bool:
        """Remove a tag from a project."""
        pass

    @abstractmethod
    async def set_tags(
        self,
        project_id: str,
        tag_ids: List[str],
        user_id: str
    ) -> List[ProjectTag]:
        """
        Set project's tags (replace all existing).

        Args:
            project_id: Project UUID
            tag_ids: New list of tag UUIDs
            user_id: User performing the action

        Returns:
            List of new ProjectTag associations
        """
        pass

    @abstractmethod
    async def count_tags_for_project(self, project_id: str) -> int:
        """Count tags on a project."""
        pass


class IAssetTagRepository(ABC):
    """
    Abstract repository interface for Asset-Tag associations.
    """

    @abstractmethod
    async def get_tags_for_asset(self, asset_id: str) -> List[Tag]:
        """Get all tags for an asset."""
        pass

    @abstractmethod
    async def add_tag(
        self,
        asset_id: str,
        tag_id: str,
        user_id: str,
        source: str = "manual"
    ) -> UserAssetTag:
        """Add a tag to an asset."""
        pass

    @abstractmethod
    async def add_tags(
        self,
        asset_id: str,
        tag_ids: List[str],
        user_id: str,
        source: str = "manual"
    ) -> List[UserAssetTag]:
        """Add multiple tags to an asset."""
        pass

    @abstractmethod
    async def remove_tag(self, asset_id: str, tag_id: str) -> bool:
        """Remove a tag from an asset."""
        pass

    @abstractmethod
    async def set_tags(
        self,
        asset_id: str,
        tag_ids: List[str],
        user_id: str,
        source: str = "manual"
    ) -> List[UserAssetTag]:
        """Set asset's tags (replace all existing)."""
        pass

    @abstractmethod
    async def count_tags_for_asset(self, asset_id: str) -> int:
        """Count tags on an asset."""
        pass
