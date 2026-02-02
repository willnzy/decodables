"""
Tag Repository Implementation - Supabase data access.

@module infrastructure.repositories.tag_repository
@version 1.0.0 (created for v3.33 Workspace + Tag Phase 1)

Implements ITagRepository, IProjectTagRepository, IAssetTagRepository
using Supabase PostgreSQL.
"""

from typing import Optional, List, Dict, Any
import logging

from domains.tag.repository import (
    ITagRepository,
    IProjectTagRepository,
    IAssetTagRepository,
)
from domains.tag.entities import (
    Tag,
    TagGroupPreset,
    ProjectTag,
    UserAssetTag,
    TagColor,
)
from core.database.retry import retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseTagRepository(ITagRepository):
    """
    Supabase implementation of Tag repository.
    """

    def __init__(self, client):
        """Initialize repository with AsyncClient."""
        if client is None:
            raise ValueError("AsyncClient required for SupabaseTagRepository")
        self._client = client

    @property
    def client(self):
        """Get AsyncClient instance."""
        return self._client

    @retry_on_network_error()
    async def get_by_id(self, tag_id: str) -> Optional[Tag]:
        """Get tag by ID."""
        try:
            result = await self.client.table("tags")\
                .select("*")\
                .eq("id", tag_id)\
                .single()\
                .execute()

            if result.data:
                return Tag.from_dict(result.data)
            return None

        except Exception as e:
            if "No rows found" in str(e) or "PGRST116" in str(e):
                return None
            logger.error(f"[TagRepository] get_by_id failed: {e}")
            raise

    @retry_on_network_error()
    async def get_by_workspace(
        self,
        workspace_id: str,
        group_name: Optional[str] = None,
        include_inactive: bool = False
    ) -> List[Tag]:
        """Get all tags for a workspace."""
        try:
            query = self.client.table("tags")\
                .select("*")\
                .eq("workspace_id", workspace_id)

            if not include_inactive:
                query = query.eq("is_active", True)

            if group_name:
                query = query.eq("group_name", group_name)

            result = await query.order("group_name").order("sort_order").execute()

            return [Tag.from_dict(row) for row in (result.data or [])]

        except Exception as e:
            logger.error(f"[TagRepository] get_by_workspace failed: {e}")
            raise

    @retry_on_network_error()
    async def get_by_name(self, workspace_id: str, name: str) -> Optional[Tag]:
        """Get tag by name within a workspace."""
        try:
            result = await self.client.table("tags")\
                .select("*")\
                .eq("workspace_id", workspace_id)\
                .ilike("name", name)\
                .eq("is_active", True)\
                .single()\
                .execute()

            if result.data:
                return Tag.from_dict(result.data)
            return None

        except Exception as e:
            if "No rows found" in str(e) or "PGRST116" in str(e):
                return None
            logger.error(f"[TagRepository] get_by_name failed: {e}")
            raise

    @retry_on_network_error()
    async def create(self, tag: Tag) -> Tag:
        """Create a new tag."""
        try:
            data = {
                "workspace_id": tag.workspace_id,
                "name": tag.name,
                "color": tag.color.value if isinstance(tag.color, TagColor) else tag.color,
                "icon": tag.icon,
                "group_name": tag.group_name,
                "sort_order": tag.sort_order,
                "created_by": tag.created_by,
                "is_active": tag.is_active,
            }

            result = await self.client.table("tags")\
                .insert(data)\
                .execute()

            if result.data:
                created = Tag.from_dict(result.data[0])
                logger.info(
                    f"[TagRepository] Created tag: id={created.id}, "
                    f"name={tag.name}, workspace={tag.workspace_id}"
                )
                return created

            return tag

        except Exception as e:
            # Check for unique constraint violation
            if "duplicate key" in str(e).lower() or "23505" in str(e):
                raise ValueError(f"Tag '{tag.name}' already exists in this workspace")
            logger.error(f"[TagRepository] create failed: {e}")
            raise

    @retry_on_network_error()
    async def create_batch(self, tags: List[Tag]) -> List[Tag]:
        """Create multiple tags at once."""
        if not tags:
            return []

        try:
            data = [
                {
                    "workspace_id": tag.workspace_id,
                    "name": tag.name,
                    "color": tag.color.value if isinstance(tag.color, TagColor) else tag.color,
                    "icon": tag.icon,
                    "group_name": tag.group_name,
                    "sort_order": tag.sort_order,
                    "created_by": tag.created_by,
                    "is_active": tag.is_active,
                }
                for tag in tags
            ]

            result = await self.client.table("tags")\
                .insert(data)\
                .execute()

            created_tags = [Tag.from_dict(row) for row in (result.data or [])]
            logger.info(f"[TagRepository] Created {len(created_tags)} tags in batch")

            return created_tags

        except Exception as e:
            logger.error(f"[TagRepository] create_batch failed: {e}")
            raise

    @retry_on_network_error()
    async def update(self, tag: Tag) -> Tag:
        """Update an existing tag."""
        try:
            if not tag.id:
                raise ValueError("Tag ID required for update")

            data = {
                "name": tag.name,
                "color": tag.color.value if isinstance(tag.color, TagColor) else tag.color,
                "icon": tag.icon,
                "group_name": tag.group_name,
                "sort_order": tag.sort_order,
                "is_active": tag.is_active,
            }

            result = await self.client.table("tags")\
                .update(data)\
                .eq("id", tag.id)\
                .execute()

            if result.data:
                return Tag.from_dict(result.data[0])

            return tag

        except Exception as e:
            if "duplicate key" in str(e).lower() or "23505" in str(e):
                raise ValueError(f"Tag '{tag.name}' already exists in this workspace")
            logger.error(f"[TagRepository] update failed: {e}")
            raise

    @retry_on_network_error()
    async def delete(self, tag_id: str) -> bool:
        """Atomically soft delete a tag and remove all associations."""
        try:
            result = await self.client.rpc("delete_tag_atomic", {
                "p_tag_id": tag_id,
            }).execute()

            # PostgREST scalar: RETURNS BOOLEAN → [true/false], not bare bool
            return bool(result.data[0]) if result.data else False

        except Exception as e:
            logger.error(f"[TagRepository] delete failed: {e}")
            raise

    @retry_on_network_error()
    async def count_by_workspace(self, workspace_id: str) -> int:
        """Count active tags in a workspace."""
        try:
            result = await self.client.table("tags")\
                .select("id", count="exact")\
                .eq("workspace_id", workspace_id)\
                .eq("is_active", True)\
                .execute()

            return result.count or 0

        except Exception as e:
            logger.error(f"[TagRepository] count_by_workspace failed: {e}")
            raise

    @retry_on_network_error()
    async def get_all_presets(self) -> List[TagGroupPreset]:
        """Get all active tag group presets."""
        try:
            result = await self.client.table("tag_group_presets")\
                .select("*")\
                .eq("is_active", True)\
                .order("sort_order")\
                .execute()

            return [TagGroupPreset.from_dict(row) for row in (result.data or [])]

        except Exception as e:
            logger.error(f"[TagRepository] get_all_presets failed: {e}")
            raise

    @retry_on_network_error()
    async def get_default_presets(self) -> List[TagGroupPreset]:
        """Get presets marked as default."""
        try:
            result = await self.client.table("tag_group_presets")\
                .select("*")\
                .eq("is_active", True)\
                .eq("is_default", True)\
                .order("sort_order")\
                .execute()

            return [TagGroupPreset.from_dict(row) for row in (result.data or [])]

        except Exception as e:
            logger.error(f"[TagRepository] get_default_presets failed: {e}")
            raise


class SupabaseProjectTagRepository(IProjectTagRepository):
    """
    Supabase implementation of Project-Tag association repository.
    """

    def __init__(self, client):
        """Initialize repository with AsyncClient."""
        if client is None:
            raise ValueError("AsyncClient required for SupabaseProjectTagRepository")
        self._client = client

    @property
    def client(self):
        """Get AsyncClient instance."""
        return self._client

    @retry_on_network_error()
    async def get_tags_for_project(self, project_id: str) -> List[Tag]:
        """Get all tags for a project."""
        try:
            # Join project_tags with tags table
            result = await self.client.table("project_tags")\
                .select("tag_id, tags(*)")\
                .eq("project_id", project_id)\
                .execute()

            tags = []
            for row in (result.data or []):
                tag_data = row.get("tags")
                if tag_data and tag_data.get("is_active", True):
                    tags.append(Tag.from_dict(tag_data))

            return tags

        except Exception as e:
            logger.error(f"[ProjectTagRepository] get_tags_for_project failed: {e}")
            raise

    @retry_on_network_error()
    async def get_projects_by_tags(
        self,
        tag_ids: List[str],
        match_mode: str = "any",
        offset: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get projects that have specified tags."""
        try:
            if not tag_ids:
                return {"project_ids": [], "total": 0, "has_more": False}

            if match_mode == "all":
                # For "all" mode, need to find projects that have ALL specified tags
                # Use RPC function for better performance
                result = await self.client.rpc(
                    "get_projects_with_all_tags",
                    {
                        "p_tag_ids": tag_ids,
                        "p_tag_count": len(tag_ids),
                        "p_offset": offset,
                        "p_limit": limit
                    }
                ).execute()
            else:
                # For "any" mode, simple query with IN clause
                result = await self.client.table("project_tags")\
                    .select("project_id", count="exact")\
                    .in_("tag_id", tag_ids)\
                    .execute()

                # Deduplicate project_ids
                project_ids = list(set(row["project_id"] for row in (result.data or [])))

                # Apply pagination
                total = len(project_ids)
                project_ids = project_ids[offset:offset + limit]

                return {
                    "project_ids": project_ids,
                    "total": total,
                    "has_more": (offset + limit) < total
                }

            # Process RPC result
            project_ids = [row["project_id"] for row in (result.data or [])]
            total = result.count or len(project_ids)

            return {
                "project_ids": project_ids,
                "total": total,
                "has_more": (offset + limit) < total
            }

        except Exception as e:
            logger.error(f"[ProjectTagRepository] get_projects_by_tags failed: {e}")
            # Fallback to simple query if RPC doesn't exist
            if "function" in str(e).lower() and "does not exist" in str(e).lower():
                logger.warning("RPC function not available, using fallback")
                return {"project_ids": [], "total": 0, "has_more": False}
            raise

    @retry_on_network_error()
    async def add_tag(self, project_id: str, tag_id: str, user_id: str) -> ProjectTag:
        """Add a tag to a project."""
        try:
            data = {
                "project_id": project_id,
                "tag_id": tag_id,
                "added_by": user_id,
            }

            result = await self.client.table("project_tags")\
                .upsert(data, on_conflict="project_id,tag_id")\
                .execute()

            if result.data:
                return ProjectTag.from_dict(result.data[0])

            return ProjectTag(project_id=project_id, tag_id=tag_id, added_by=user_id)

        except Exception as e:
            logger.error(f"[ProjectTagRepository] add_tag failed: {e}")
            raise

    @retry_on_network_error()
    async def add_tags(
        self,
        project_id: str,
        tag_ids: List[str],
        user_id: str
    ) -> List[ProjectTag]:
        """Add multiple tags to a project."""
        if not tag_ids:
            return []

        try:
            data = [
                {
                    "project_id": project_id,
                    "tag_id": tag_id,
                    "added_by": user_id,
                }
                for tag_id in tag_ids
            ]

            result = await self.client.table("project_tags")\
                .upsert(data, on_conflict="project_id,tag_id")\
                .execute()

            return [ProjectTag.from_dict(row) for row in (result.data or [])]

        except Exception as e:
            logger.error(f"[ProjectTagRepository] add_tags failed: {e}")
            raise

    @retry_on_network_error()
    async def remove_tag(self, project_id: str, tag_id: str) -> bool:
        """Remove a tag from a project."""
        try:
            result = await self.client.table("project_tags")\
                .delete()\
                .eq("project_id", project_id)\
                .eq("tag_id", tag_id)\
                .execute()

            return bool(result.data)

        except Exception as e:
            logger.error(f"[ProjectTagRepository] remove_tag failed: {e}")
            raise

    @retry_on_network_error()
    async def set_tags(
        self,
        project_id: str,
        tag_ids: List[str],
        user_id: str
    ) -> List[ProjectTag]:
        """Atomically set project's tags (replace all existing)."""
        try:
            await self.client.rpc("set_project_tags_atomic", {
                "p_project_id": project_id,
                "p_tag_ids": tag_ids,
                "p_user_id": user_id,
            }).execute()

            # Return the newly set tags
            if tag_ids:
                return await self.get_tags_for_project(project_id)
            return []

        except Exception as e:
            logger.error(f"[ProjectTagRepository] set_tags failed: {e}")
            raise

    @retry_on_network_error()
    async def count_tags_for_project(self, project_id: str) -> int:
        """Count tags on a project."""
        try:
            result = await self.client.table("project_tags")\
                .select("tag_id", count="exact")\
                .eq("project_id", project_id)\
                .execute()

            return result.count or 0

        except Exception as e:
            logger.error(f"[ProjectTagRepository] count_tags_for_project failed: {e}")
            raise


class SupabaseAssetTagRepository(IAssetTagRepository):
    """
    Supabase implementation of Asset-Tag association repository.
    """

    def __init__(self, client):
        """Initialize repository with AsyncClient."""
        if client is None:
            raise ValueError("AsyncClient required for SupabaseAssetTagRepository")
        self._client = client

    @property
    def client(self):
        """Get AsyncClient instance."""
        return self._client

    @retry_on_network_error()
    async def get_tags_for_asset(self, asset_id: str) -> List[Tag]:
        """Get all tags for an asset."""
        try:
            # Join user_asset_tags with tags table
            result = await self.client.table("user_asset_tags")\
                .select("tag_id, source, tags(*)")\
                .eq("asset_id", asset_id)\
                .execute()

            tags = []
            for row in (result.data or []):
                tag_data = row.get("tags")
                if tag_data and tag_data.get("is_active", True):
                    tags.append(Tag.from_dict(tag_data))

            return tags

        except Exception as e:
            logger.error(f"[AssetTagRepository] get_tags_for_asset failed: {e}")
            raise

    @retry_on_network_error()
    async def add_tag(
        self,
        asset_id: str,
        tag_id: str,
        user_id: str,
        source: str = "manual"
    ) -> UserAssetTag:
        """Add a tag to an asset."""
        try:
            data = {
                "asset_id": asset_id,
                "tag_id": tag_id,
                "added_by": user_id,
                "source": source,
            }

            result = await self.client.table("user_asset_tags")\
                .upsert(data, on_conflict="asset_id,tag_id")\
                .execute()

            if result.data:
                return UserAssetTag.from_dict(result.data[0])

            return UserAssetTag(
                asset_id=asset_id,
                tag_id=tag_id,
                added_by=user_id,
                source=source
            )

        except Exception as e:
            logger.error(f"[AssetTagRepository] add_tag failed: {e}")
            raise

    @retry_on_network_error()
    async def add_tags(
        self,
        asset_id: str,
        tag_ids: List[str],
        user_id: str,
        source: str = "manual"
    ) -> List[UserAssetTag]:
        """Add multiple tags to an asset."""
        if not tag_ids:
            return []

        try:
            data = [
                {
                    "asset_id": asset_id,
                    "tag_id": tag_id,
                    "added_by": user_id,
                    "source": source,
                }
                for tag_id in tag_ids
            ]

            result = await self.client.table("user_asset_tags")\
                .upsert(data, on_conflict="asset_id,tag_id")\
                .execute()

            return [UserAssetTag.from_dict(row) for row in (result.data or [])]

        except Exception as e:
            logger.error(f"[AssetTagRepository] add_tags failed: {e}")
            raise

    @retry_on_network_error()
    async def remove_tag(self, asset_id: str, tag_id: str) -> bool:
        """Remove a tag from an asset."""
        try:
            result = await self.client.table("user_asset_tags")\
                .delete()\
                .eq("asset_id", asset_id)\
                .eq("tag_id", tag_id)\
                .execute()

            return bool(result.data)

        except Exception as e:
            logger.error(f"[AssetTagRepository] remove_tag failed: {e}")
            raise

    @retry_on_network_error()
    async def set_tags(
        self,
        asset_id: str,
        tag_ids: List[str],
        user_id: str,
        source: str = "manual"
    ) -> List[UserAssetTag]:
        """Atomically set asset's tags (replace all existing)."""
        try:
            await self.client.rpc("set_asset_tags_atomic", {
                "p_asset_id": asset_id,
                "p_tag_ids": tag_ids,
                "p_user_id": user_id,
                "p_source": source,
            }).execute()

            # Return the newly set tags
            if tag_ids:
                return await self.get_tags_for_asset(asset_id)
            return []

        except Exception as e:
            logger.error(f"[AssetTagRepository] set_tags failed: {e}")
            raise

    @retry_on_network_error()
    async def count_tags_for_asset(self, asset_id: str) -> int:
        """Count tags on an asset."""
        try:
            result = await self.client.table("user_asset_tags")\
                .select("tag_id", count="exact")\
                .eq("asset_id", asset_id)\
                .execute()

            return result.count or 0

        except Exception as e:
            logger.error(f"[AssetTagRepository] count_tags_for_asset failed: {e}")
            raise
