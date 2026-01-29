"""
Folder Repository Implementation - Supabase data access.

@module infrastructure.repositories.folder_repository
@version 1.0.0 (created for v3.33 Workspace + Tag Phase 2.6)

Implements IFolderRepository using Supabase PostgreSQL.
"""

from typing import Optional, List, Dict, Any
import logging

from domains.folder.repository import IFolderRepository
from domains.folder.entities import Folder, FolderType
from core.database.retry import retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseFolderRepository(IFolderRepository):
    """
    Supabase implementation of Folder repository.

    Provides CRUD operations for folders with workspace and type scoping.
    """

    def __init__(self, client):
        """
        Initialize repository with AsyncClient.

        Args:
            client: AsyncClient instance (required)

        Raises:
            ValueError: If client is None
        """
        if client is None:
            raise ValueError("AsyncClient required for SupabaseFolderRepository")
        self._client = client

    @property
    def client(self):
        """Get AsyncClient instance."""
        return self._client

    @retry_on_network_error()
    async def get_by_id(self, folder_id: str) -> Optional[Folder]:
        """Get folder by ID."""
        try:
            result = await self.client.table("folders")\
                .select("*")\
                .eq("id", folder_id)\
                .single()\
                .execute()

            if result.data:
                return Folder.from_dict(result.data)
            return None

        except Exception as e:
            # single() raises when no row found
            if "No rows found" in str(e) or "PGRST116" in str(e):
                return None
            logger.error(f"[FolderRepository] get_by_id failed: {e}")
            raise

    @retry_on_network_error()
    async def get_by_workspace(
        self,
        workspace_id: str,
        folder_type: FolderType,
    ) -> List[Folder]:
        """Get all folders of a specific type in a workspace."""
        try:
            result = await self.client.table("folders")\
                .select("*")\
                .eq("workspace_id", workspace_id)\
                .eq("folder_type", folder_type.value)\
                .order("sort_order")\
                .order("created_at")\
                .execute()

            folders = [Folder.from_dict(row) for row in (result.data or [])]

            # Enrich with item counts
            for folder in folders:
                folder.item_count = await self.count_items(folder.id)

            return folders

        except Exception as e:
            logger.error(f"[FolderRepository] get_by_workspace failed: {e}")
            raise

    @retry_on_network_error()
    async def get_by_workspace_and_name(
        self,
        workspace_id: str,
        folder_type: FolderType,
        name: str,
    ) -> Optional[Folder]:
        """Get folder by workspace, type, and name."""
        try:
            result = await self.client.table("folders")\
                .select("*")\
                .eq("workspace_id", workspace_id)\
                .eq("folder_type", folder_type.value)\
                .eq("name", name)\
                .single()\
                .execute()

            if result.data:
                return Folder.from_dict(result.data)
            return None

        except Exception as e:
            # single() raises when no row found
            if "No rows found" in str(e) or "PGRST116" in str(e):
                return None
            logger.error(f"[FolderRepository] get_by_workspace_and_name failed: {e}")
            raise

    @retry_on_network_error()
    async def create(self, folder: Folder) -> Folder:
        """Create a new folder."""
        try:
            # Check for duplicate name
            existing = await self.get_by_workspace_and_name(
                folder.workspace_id,
                folder.folder_type,
                folder.name,
            )
            if existing:
                raise ValueError(f"Folder with name '{folder.name}' already exists")

            data = {
                "workspace_id": folder.workspace_id,
                "folder_type": folder.folder_type.value if isinstance(folder.folder_type, FolderType) else folder.folder_type,
                "name": folder.name,
                "color": folder.color.value if hasattr(folder.color, 'value') else folder.color,
                "sort_order": folder.sort_order,
                "created_by": folder.created_by,
            }

            result = await self.client.table("folders")\
                .insert(data)\
                .execute()

            if result.data:
                created = Folder.from_dict(result.data[0])
                logger.info(
                    f"[FolderRepository] Created folder: "
                    f"id={created.id}, name={folder.name}, type={folder.folder_type}"
                )
                return created

            return folder

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"[FolderRepository] create failed: {e}")
            raise

    @retry_on_network_error()
    async def update(self, folder: Folder) -> Folder:
        """Update an existing folder."""
        try:
            if not folder.id:
                raise ValueError("Folder ID required for update")

            data = {
                "name": folder.name,
                "color": folder.color.value if hasattr(folder.color, 'value') else folder.color,
                "sort_order": folder.sort_order,
            }

            result = await self.client.table("folders")\
                .update(data)\
                .eq("id", folder.id)\
                .execute()

            if result.data:
                return Folder.from_dict(result.data[0])

            return folder

        except Exception as e:
            logger.error(f"[FolderRepository] update failed: {e}")
            raise

    @retry_on_network_error()
    async def update_partial(self, folder_id: str, data: dict) -> Optional[Folder]:
        """Partially update a folder."""
        try:
            if not folder_id:
                raise ValueError("Folder ID required for update")

            # Only allow safe fields to be updated
            allowed_fields = {"name", "color", "sort_order"}
            update_data = {}

            for k, v in data.items():
                if k in allowed_fields:
                    # Handle enum values
                    if k == "color" and hasattr(v, 'value'):
                        update_data[k] = v.value
                    else:
                        update_data[k] = v

            if not update_data:
                # No valid fields to update, fetch and return current
                return await self.get_by_id(folder_id)

            result = await self.client.table("folders")\
                .update(update_data)\
                .eq("id", folder_id)\
                .execute()

            if result.data:
                logger.info(
                    f"[FolderRepository] Updated folder: "
                    f"id={folder_id}, fields={list(update_data.keys())}"
                )
                return Folder.from_dict(result.data[0])

            return None

        except Exception as e:
            logger.error(f"[FolderRepository] update_partial failed: {e}")
            raise

    @retry_on_network_error()
    async def delete(self, folder_id: str) -> bool:
        """Delete a folder."""
        try:
            if not folder_id:
                raise ValueError("Folder ID required for delete")

            result = await self.client.table("folders")\
                .delete()\
                .eq("id", folder_id)\
                .execute()

            # Check if deletion was successful
            # Note: Items in folder will have folder_id set to NULL (ON DELETE SET NULL)
            success = result.data is not None

            if success:
                logger.info(f"[FolderRepository] Deleted folder: id={folder_id}")

            return success

        except Exception as e:
            logger.error(f"[FolderRepository] delete failed: {e}")
            raise

    @retry_on_network_error()
    async def exists(self, folder_id: str) -> bool:
        """Check if a folder exists."""
        try:
            result = await self.client.table("folders")\
                .select("id")\
                .eq("id", folder_id)\
                .execute()

            return bool(result.data)

        except Exception as e:
            logger.error(f"[FolderRepository] exists failed: {e}")
            raise

    @retry_on_network_error()
    async def count_items(self, folder_id: str) -> int:
        """Count items (projects or assets) in a folder."""
        try:
            # First get the folder to know its type
            folder = await self.get_by_id(folder_id)
            if not folder:
                return 0

            # Count items based on folder type
            if folder.folder_type == FolderType.PROJECT:
                result = await self.client.table("projects")\
                    .select("id", count="exact")\
                    .eq("folder_id", folder_id)\
                    .eq("is_deleted", False)\
                    .execute()
            else:  # ASSET
                result = await self.client.table("assets")\
                    .select("id", count="exact")\
                    .eq("folder_id", folder_id)\
                    .eq("is_deleted", False)\
                    .execute()

            return result.count if result.count else 0

        except Exception as e:
            logger.error(f"[FolderRepository] count_items failed: {e}")
            return 0

    @retry_on_network_error()
    async def count_items_by_type(
        self,
        folder_id: str,
        folder_type: FolderType,
        user_id: str,
    ) -> dict:
        """
        Count items in a folder by marketplace status.

        For project folders:
        - bought_count: Projects with is_purchased=True
        - selling_count: Projects with active marketplace listings

        Args:
            folder_id: Folder UUID
            folder_type: Type of folder (project or asset) - avoids redundant DB lookup
            user_id: User ID (needed for checking marketplace_listings)

        Returns:
            Dict with 'total', 'bought_count', 'selling_count'
        """
        try:
            if folder_type == FolderType.PROJECT:
                # Total count
                total_result = await self.client.table("projects")\
                    .select("id", count="exact")\
                    .eq("folder_id", folder_id)\
                    .eq("is_deleted", False)\
                    .execute()
                total = total_result.count or 0

                # Bought count (is_purchased = True)
                bought_result = await self.client.table("projects")\
                    .select("id", count="exact")\
                    .eq("folder_id", folder_id)\
                    .eq("is_deleted", False)\
                    .eq("is_purchased", True)\
                    .execute()
                bought_count = bought_result.count or 0

                # Selling count - get project IDs in this folder, then check marketplace_listings
                projects_result = await self.client.table("projects")\
                    .select("id")\
                    .eq("folder_id", folder_id)\
                    .eq("is_deleted", False)\
                    .execute()
                project_ids = [p["id"] for p in (projects_result.data or [])]

                selling_count = 0
                if project_ids:
                    # Count projects that have active marketplace listings
                    listings_result = await self.client.table("marketplace_listings")\
                        .select("resource_id", count="exact")\
                        .eq("seller_id", user_id)\
                        .eq("resource_type", "project")\
                        .eq("is_deleted", False)\
                        .in_("resource_id", project_ids)\
                        .execute()
                    selling_count = listings_result.count or 0

                return {
                    "total": total,
                    "bought_count": bought_count,
                    "selling_count": selling_count,
                }

            else:  # ASSET
                # For assets, similar logic but using assets table
                total_result = await self.client.table("assets")\
                    .select("id", count="exact")\
                    .eq("folder_id", folder_id)\
                    .eq("is_deleted", False)\
                    .execute()
                total = total_result.count or 0

                # Bought count
                bought_result = await self.client.table("assets")\
                    .select("id", count="exact")\
                    .eq("folder_id", folder_id)\
                    .eq("is_deleted", False)\
                    .eq("is_purchased", True)\
                    .execute()
                bought_count = bought_result.count or 0

                # Selling count
                assets_result = await self.client.table("assets")\
                    .select("id")\
                    .eq("folder_id", folder_id)\
                    .eq("is_deleted", False)\
                    .execute()
                asset_ids = [a["id"] for a in (assets_result.data or [])]

                selling_count = 0
                if asset_ids:
                    listings_result = await self.client.table("marketplace_listings")\
                        .select("resource_id", count="exact")\
                        .eq("seller_id", user_id)\
                        .eq("resource_type", "asset")\
                        .eq("is_deleted", False)\
                        .in_("resource_id", asset_ids)\
                        .execute()
                    selling_count = listings_result.count or 0

                return {
                    "total": total,
                    "bought_count": bought_count,
                    "selling_count": selling_count,
                }

        except Exception as e:
            logger.error(f"[FolderRepository] count_items_by_type failed: {e}")
            return {"total": 0, "bought_count": 0, "selling_count": 0}

    @retry_on_network_error()
    async def get_preview_items(
        self,
        folder_id: str,
        folder_type: FolderType,
        limit: int = 4,
    ) -> List[Dict[str, Any]]:
        """Get preview items (thumbnails) for a folder."""
        try:
            # Projects have title + thumbnail_url; assets have url (the image itself)
            if folder_type == FolderType.PROJECT:
                result = await self.client.table("projects")\
                    .select("id, title, thumbnail_url")\
                    .eq("folder_id", folder_id)\
                    .eq("is_deleted", False)\
                    .order("updated_at", desc=True)\
                    .limit(limit)\
                    .execute()

                items = []
                for row in (result.data or []):
                    items.append({
                        "id": row["id"],
                        "title": row.get("title", ""),
                        "thumbnailUrl": row.get("thumbnail_url"),
                    })
            else:
                result = await self.client.table("assets")\
                    .select("id, url")\
                    .eq("folder_id", folder_id)\
                    .eq("is_deleted", False)\
                    .order("updated_at", desc=True)\
                    .limit(limit)\
                    .execute()

                items = []
                for row in (result.data or []):
                    items.append({
                        "id": row["id"],
                        "title": "",
                        "thumbnailUrl": row.get("url"),
                    })

            return items

        except Exception as e:
            logger.error(f"[FolderRepository] get_preview_items failed: {e}")
            return []

    @retry_on_network_error()
    async def reorder(
        self,
        workspace_id: str,
        folder_type: FolderType,
        folder_ids: List[str],
    ) -> bool:
        """Reorder folders within a workspace."""
        try:
            # Update sort_order for each folder
            for index, folder_id in enumerate(folder_ids):
                await self.client.table("folders")\
                    .update({"sort_order": index})\
                    .eq("id", folder_id)\
                    .eq("workspace_id", workspace_id)\
                    .eq("folder_type", folder_type.value)\
                    .execute()

            logger.info(
                f"[FolderRepository] Reordered folders: "
                f"workspace={workspace_id}, type={folder_type.value}, count={len(folder_ids)}"
            )
            return True

        except Exception as e:
            logger.error(f"[FolderRepository] reorder failed: {e}")
            raise
