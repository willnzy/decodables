"""
Tag Domain Service

Core business logic for Tag domain.

@module domains.tag.service
@version 1.0.0 (created for v3.33 Workspace + Tag Phase 1)
"""

from typing import Optional, List, Dict, Any
import logging
import re

from .entities import Tag, TagColor, TagGroupPreset, ProjectTag, UserAssetTag
from .repository import ITagRepository, IProjectTagRepository, IAssetTagRepository

logger = logging.getLogger(__name__)


# Default limits (can be overridden from system_configs)
DEFAULT_MAX_TAGS_PER_WORKSPACE = 100
DEFAULT_MAX_TAGS_PER_PROJECT = 10
DEFAULT_MAX_TAGS_PER_ASSET = 10


class TagService:
    """
    Tag service - manages tag CRUD and preset operations.
    """

    def __init__(
        self,
        tag_repository: ITagRepository,
        config_service=None,
    ):
        """
        Initialize service.

        Args:
            tag_repository: ITagRepository implementation
            config_service: Optional config service for limit settings
        """
        self._repo = tag_repository
        self._config = config_service

    async def _get_max_tags_per_workspace(self) -> int:
        """Get max tags per workspace from config."""
        if self._config:
            try:
                return await self._config.get_int(
                    "tag.max_tags_per_workspace",
                    DEFAULT_MAX_TAGS_PER_WORKSPACE
                )
            except Exception:
                pass
        return DEFAULT_MAX_TAGS_PER_WORKSPACE

    async def list_tags(
        self,
        workspace_id: str,
        group_name: Optional[str] = None
    ) -> List[Tag]:
        """
        Get all tags for a workspace.

        Args:
            workspace_id: Workspace UUID
            group_name: Optional filter by group

        Returns:
            List of Tag entities, grouped and sorted
        """
        return await self._repo.get_by_workspace(workspace_id, group_name)

    async def get_tags_by_group(self, workspace_id: str) -> Dict[str, List[Tag]]:
        """
        Get tags organized by group.

        Args:
            workspace_id: Workspace UUID

        Returns:
            Dict mapping group_name to list of tags
        """
        tags = await self._repo.get_by_workspace(workspace_id)

        groups: Dict[str, List[Tag]] = {}
        for tag in tags:
            group_key = tag.group_name or "ungrouped"
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(tag)

        return groups

    async def get_tag(self, tag_id: str) -> Optional[Tag]:
        """Get tag by ID."""
        return await self._repo.get_by_id(tag_id)

    async def create_tag(
        self,
        workspace_id: str,
        name: str,
        color: TagColor,
        created_by: str,
        group_name: Optional[str] = None,
        icon: Optional[str] = None,
    ) -> Tag:
        """
        Create a new tag.

        Args:
            workspace_id: Workspace UUID
            name: Tag name
            color: Tag color
            created_by: User ID who created
            group_name: Optional group name
            icon: Optional icon (emoji)

        Returns:
            Created Tag entity

        Raises:
            ValueError: If name is empty, duplicate, or limit exceeded
        """
        # Validate name
        name = name.strip()
        if not name:
            raise ValueError("Tag name cannot be empty")

        if len(name) > 50:
            raise ValueError("Tag name cannot exceed 50 characters")

        # WS-08: XSS prevention — reject HTML/script patterns
        if re.search(r"<[^>]*script|javascript:|on\w+=", name, re.IGNORECASE):
            raise ValueError("Tag name contains invalid characters")
        # Strip any HTML tags
        name = re.sub(r"<[^>]*>", "", name).strip()
        if not name:
            raise ValueError("Tag name cannot be empty after sanitization")

        # Check if name already exists
        existing = await self._repo.get_by_name(workspace_id, name)
        if existing:
            raise ValueError(f"Tag '{name}' already exists in this workspace")

        # Check workspace tag limit
        max_tags = await self._get_max_tags_per_workspace()
        current_count = await self._repo.count_by_workspace(workspace_id)
        if current_count >= max_tags:
            raise ValueError(
                f"Workspace has reached the maximum of {max_tags} tags"
            )

        # Create tag
        tag = Tag(
            workspace_id=workspace_id,
            name=name,
            color=color,
            icon=icon,
            group_name=group_name,
            created_by=created_by,
        )

        return await self._repo.create(tag)

    async def update_tag(
        self,
        tag_id: str,
        name: Optional[str] = None,
        color: Optional[TagColor] = None,
        icon: Optional[str] = None,
        group_name: Optional[str] = None,
    ) -> Tag:
        """
        Update an existing tag.

        Args:
            tag_id: Tag UUID
            name: New name (optional)
            color: New color (optional)
            icon: New icon (optional)
            group_name: New group (optional)

        Returns:
            Updated Tag entity

        Raises:
            ValueError: If tag not found or name is duplicate
        """
        tag = await self._repo.get_by_id(tag_id)
        if not tag:
            raise ValueError(f"Tag not found: {tag_id}")

        # Update fields if provided
        if name is not None:
            name = name.strip()
            if not name:
                raise ValueError("Tag name cannot be empty")
            if len(name) > 50:
                raise ValueError("Tag name cannot exceed 50 characters")
            # WS-08: XSS prevention
            if re.search(r"<[^>]*script|javascript:|on\w+=", name, re.IGNORECASE):
                raise ValueError("Tag name contains invalid characters")
            name = re.sub(r"<[^>]*>", "", name).strip()
            if not name:
                raise ValueError("Tag name cannot be empty after sanitization")

            # Check for duplicate name (if changing)
            if name.lower() != tag.name.lower():
                existing = await self._repo.get_by_name(tag.workspace_id, name)
                if existing:
                    raise ValueError(f"Tag '{name}' already exists in this workspace")
            tag.name = name

        if color is not None:
            tag.color = color

        if icon is not None:
            tag.icon = icon if icon else None

        if group_name is not None:
            tag.group_name = group_name if group_name else None

        return await self._repo.update(tag)

    async def delete_tag(self, tag_id: str) -> bool:
        """
        Delete a tag (soft delete).

        Also removes all project and asset associations.

        Args:
            tag_id: Tag UUID

        Returns:
            True if deleted successfully
        """
        return await self._repo.delete(tag_id)

    async def get_or_create_tag(
        self,
        workspace_id: str,
        name: str,
        created_by: str,
        color: TagColor = TagColor.GRAY,
        group_name: Optional[str] = None,
    ) -> Tag:
        """
        Get existing tag by name, or create if not exists.

        Useful for AI recommendations that may suggest new tags.

        Args:
            workspace_id: Workspace UUID
            name: Tag name
            created_by: User ID
            color: Default color if creating
            group_name: Default group if creating

        Returns:
            Existing or newly created Tag
        """
        existing = await self._repo.get_by_name(workspace_id, name)
        if existing:
            return existing

        return await self.create_tag(
            workspace_id=workspace_id,
            name=name,
            color=color,
            created_by=created_by,
            group_name=group_name,
        )

    async def apply_default_presets(
        self,
        workspace_id: str,
        user_id: str
    ) -> List[Tag]:
        """
        Apply default preset tag groups to a workspace.

        Called when a new workspace is created.

        Args:
            workspace_id: Workspace UUID
            user_id: Owner user ID

        Returns:
            List of created Tag entities
        """
        presets = await self._repo.get_default_presets()
        if not presets:
            logger.info(f"[TagService] No default presets to apply for workspace {workspace_id}")
            return []

        tags_to_create = []
        for preset in presets:
            for i, tag_data in enumerate(preset.preset_tags):
                tag = Tag(
                    workspace_id=workspace_id,
                    name=tag_data.get("name", ""),
                    color=TagColor.from_str(tag_data.get("color", "gray")),
                    icon=tag_data.get("icon"),
                    group_name=preset.group_name,
                    sort_order=i,
                    created_by=user_id,
                )
                tags_to_create.append(tag)

        if tags_to_create:
            created = await self._repo.create_batch(tags_to_create)
            logger.info(
                f"[TagService] Applied {len(created)} preset tags to workspace {workspace_id}"
            )
            return created

        return []

    async def get_all_presets(self) -> List[TagGroupPreset]:
        """Get all available tag group presets."""
        return await self._repo.get_all_presets()


class ProjectTagService:
    """
    Service for managing project-tag associations.
    """

    def __init__(
        self,
        project_tag_repository: IProjectTagRepository,
        tag_repository: ITagRepository,
        config_service=None,
    ):
        """Initialize service."""
        self._repo = project_tag_repository
        self._tag_repo = tag_repository
        self._config = config_service

    async def _get_max_tags_per_project(self) -> int:
        """Get max tags per project from config."""
        if self._config:
            try:
                return await self._config.get_int(
                    "tag.max_tags_per_project",
                    DEFAULT_MAX_TAGS_PER_PROJECT
                )
            except Exception:
                pass
        return DEFAULT_MAX_TAGS_PER_PROJECT

    async def get_project_tags(self, project_id: str) -> List[Tag]:
        """Get all tags for a project."""
        return await self._repo.get_tags_for_project(project_id)

    async def add_tags(
        self,
        project_id: str,
        tag_ids: List[str],
        user_id: str
    ) -> List[Tag]:
        """
        Add tags to a project.

        Args:
            project_id: Project UUID
            tag_ids: List of tag UUIDs to add
            user_id: User performing the action

        Returns:
            List of added Tag entities

        Raises:
            ValueError: If limit exceeded
        """
        if not tag_ids:
            return []

        # Check limit
        max_tags = await self._get_max_tags_per_project()
        current_count = await self._repo.count_tags_for_project(project_id)

        if current_count + len(tag_ids) > max_tags:
            raise ValueError(
                f"Cannot add {len(tag_ids)} tags. "
                f"Project already has {current_count}/{max_tags} tags."
            )

        # Add tags
        await self._repo.add_tags(project_id, tag_ids, user_id)

        # Return updated tags
        return await self._repo.get_tags_for_project(project_id)

    async def remove_tag(self, project_id: str, tag_id: str) -> bool:
        """Remove a tag from a project."""
        return await self._repo.remove_tag(project_id, tag_id)

    async def set_tags(
        self,
        project_id: str,
        tag_ids: List[str],
        user_id: str
    ) -> List[Tag]:
        """
        Set project's tags (replace all existing).

        Args:
            project_id: Project UUID
            tag_ids: New list of tag UUIDs
            user_id: User performing the action

        Returns:
            List of Tag entities

        Raises:
            ValueError: If limit exceeded
        """
        # Check limit
        max_tags = await self._get_max_tags_per_project()
        if len(tag_ids) > max_tags:
            raise ValueError(
                f"Cannot set {len(tag_ids)} tags. Maximum is {max_tags}."
            )

        # Set tags
        await self._repo.set_tags(project_id, tag_ids, user_id)

        # Return updated tags
        return await self._repo.get_tags_for_project(project_id)

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
        return await self._repo.get_projects_by_tags(
            tag_ids, match_mode, offset, limit
        )


class AssetTagService:
    """
    Service for managing asset-tag associations.
    """

    def __init__(
        self,
        asset_tag_repository: IAssetTagRepository,
        tag_repository: ITagRepository,
        config_service=None,
    ):
        """Initialize service."""
        self._repo = asset_tag_repository
        self._tag_repo = tag_repository
        self._config = config_service

    async def _get_max_tags_per_asset(self) -> int:
        """Get max tags per asset from config."""
        if self._config:
            try:
                return await self._config.get_int(
                    "tag.max_tags_per_asset",
                    DEFAULT_MAX_TAGS_PER_ASSET
                )
            except Exception:
                pass
        return DEFAULT_MAX_TAGS_PER_ASSET

    async def get_asset_tags(self, asset_id: str) -> List[Tag]:
        """Get all tags for an asset."""
        return await self._repo.get_tags_for_asset(asset_id)

    async def add_tags(
        self,
        asset_id: str,
        tag_ids: List[str],
        user_id: str,
        source: str = "manual"
    ) -> List[Tag]:
        """
        Add tags to an asset.

        Args:
            asset_id: Asset UUID
            tag_ids: List of tag UUIDs to add
            user_id: User performing the action
            source: "manual" or "ai_recommended"

        Returns:
            List of added Tag entities

        Raises:
            ValueError: If limit exceeded
        """
        if not tag_ids:
            return []

        # Check limit
        max_tags = await self._get_max_tags_per_asset()
        current_count = await self._repo.count_tags_for_asset(asset_id)

        if current_count + len(tag_ids) > max_tags:
            raise ValueError(
                f"Cannot add {len(tag_ids)} tags. "
                f"Asset already has {current_count}/{max_tags} tags."
            )

        # Add tags
        await self._repo.add_tags(asset_id, tag_ids, user_id, source)

        # Return updated tags
        return await self._repo.get_tags_for_asset(asset_id)

    async def remove_tag(self, asset_id: str, tag_id: str) -> bool:
        """Remove a tag from an asset."""
        return await self._repo.remove_tag(asset_id, tag_id)

    async def set_tags(
        self,
        asset_id: str,
        tag_ids: List[str],
        user_id: str,
        source: str = "manual"
    ) -> List[Tag]:
        """
        Set asset's tags (replace all existing).

        Args:
            asset_id: Asset UUID
            tag_ids: New list of tag UUIDs
            user_id: User performing the action
            source: "manual" or "ai_recommended"

        Returns:
            List of Tag entities

        Raises:
            ValueError: If limit exceeded
        """
        # Check limit
        max_tags = await self._get_max_tags_per_asset()
        if len(tag_ids) > max_tags:
            raise ValueError(
                f"Cannot set {len(tag_ids)} tags. Maximum is {max_tags}."
            )

        # Set tags
        await self._repo.set_tags(asset_id, tag_ids, user_id, source)

        # Return updated tags
        return await self._repo.get_tags_for_asset(asset_id)
