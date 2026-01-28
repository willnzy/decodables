"""
Folder Domain Service

Core business logic for Folder domain.

@module domains.folder.service
@version 1.0.0 (created for v3.33 Workspace + Tag Phase 2.6)
"""

from typing import Optional, List
import logging

from .entities import Folder, FolderColor, FolderType
from .repository import IFolderRepository

logger = logging.getLogger(__name__)


class FolderService:
    """
    Folder service.

    Manages folder operations with workspace-level scoping and ownership validation.
    """

    def __init__(self, repository: IFolderRepository):
        """
        Initialize service with repository.

        Args:
            repository: IFolderRepository implementation
        """
        self._repo = repository

    # ==========================================
    # CRUD Operations
    # ==========================================

    async def create_folder(
        self,
        workspace_id: str,
        folder_type: FolderType,
        name: str,
        created_by: str,
        color: Optional[FolderColor] = None,
    ) -> Folder:
        """
        Create a new folder.

        Args:
            workspace_id: UUID of the workspace
            folder_type: Type of folder (project or asset)
            name: Folder name (must be unique within workspace/type)
            created_by: Clerk user_id of the creator
            color: Folder color (default: slate)

        Returns:
            Created Folder entity

        Raises:
            ValueError: If folder name already exists
        """
        folder = Folder.create_new(
            workspace_id=workspace_id,
            folder_type=folder_type,
            name=name.strip(),
            created_by=created_by,
            color=color or FolderColor.SLATE,
        )

        created = await self._repo.create(folder)

        logger.info(
            f"[FolderService] Created folder: "
            f"id={created.id}, name={name}, type={folder_type.value}"
        )

        return created

    async def get_folder(self, folder_id: str) -> Optional[Folder]:
        """
        Get folder by ID.

        Args:
            folder_id: Folder UUID

        Returns:
            Folder entity or None if not found
        """
        return await self._repo.get_by_id(folder_id)

    async def list_folders(
        self,
        workspace_id: str,
        folder_type: FolderType,
    ) -> List[Folder]:
        """
        List all folders of a specific type in a workspace.

        Args:
            workspace_id: Workspace UUID
            folder_type: Type of folder (project or asset)

        Returns:
            List of Folder entities ordered by sort_order
        """
        return await self._repo.get_by_workspace(workspace_id, folder_type)

    async def list_folders_with_counts(
        self,
        workspace_id: str,
        folder_type: FolderType,
        user_id: str,
    ) -> List[Folder]:
        """
        List all folders with bought/selling counts for filtering.

        v3.34: Added for Bought/Selling tab folder filtering.
        Returns folders with item_count, bought_count, and selling_count populated.

        Args:
            workspace_id: Workspace UUID
            folder_type: Type of folder (project or asset)
            user_id: User ID (for checking marketplace_listings)

        Returns:
            List of Folder entities with counts populated
        """
        folders = await self._repo.get_by_workspace(workspace_id, folder_type)

        # Enrich each folder with bought/selling counts
        for folder in folders:
            counts = await self._repo.count_items_by_type(folder.id, user_id)
            folder.item_count = counts["total"]
            folder.bought_count = counts["bought_count"]
            folder.selling_count = counts["selling_count"]

        return folders

    async def update_folder(
        self,
        folder_id: str,
        name: Optional[str] = None,
        color: Optional[FolderColor] = None,
    ) -> Optional[Folder]:
        """
        Update an existing folder.

        Args:
            folder_id: Folder UUID
            name: New folder name (optional)
            color: New folder color (optional)

        Returns:
            Updated Folder entity or None if not found

        Raises:
            ValueError: If new name conflicts with existing folder
        """
        update_data = {}

        if name is not None:
            # Check for name conflict
            folder = await self._repo.get_by_id(folder_id)
            if folder:
                existing = await self._repo.get_by_workspace_and_name(
                    folder.workspace_id,
                    folder.folder_type,
                    name.strip(),
                )
                if existing and existing.id != folder_id:
                    raise ValueError(f"Folder with name '{name}' already exists")

            update_data["name"] = name.strip()

        if color is not None:
            update_data["color"] = color

        if not update_data:
            return await self._repo.get_by_id(folder_id)

        updated = await self._repo.update_partial(folder_id, update_data)

        if updated:
            logger.info(
                f"[FolderService] Updated folder: "
                f"id={folder_id}, fields={list(update_data.keys())}"
            )

        return updated

    async def delete_folder(self, folder_id: str) -> bool:
        """
        Delete a folder.

        Note: Items in the folder will be moved to root (folder_id=NULL)
        due to ON DELETE SET NULL constraint.

        Args:
            folder_id: Folder UUID

        Returns:
            True if deleted successfully
        """
        # Get folder for logging
        folder = await self._repo.get_by_id(folder_id)

        success = await self._repo.delete(folder_id)

        if success and folder:
            logger.info(
                f"[FolderService] Deleted folder: "
                f"id={folder_id}, name={folder.name}"
            )

        return success

    async def reorder_folders(
        self,
        workspace_id: str,
        folder_type: FolderType,
        folder_ids: List[str],
    ) -> bool:
        """
        Reorder folders within a workspace.

        Args:
            workspace_id: Workspace UUID
            folder_type: Type of folder
            folder_ids: Ordered list of folder IDs

        Returns:
            True if reordered successfully
        """
        success = await self._repo.reorder(workspace_id, folder_type, folder_ids)

        if success:
            logger.info(
                f"[FolderService] Reordered folders: "
                f"workspace={workspace_id}, type={folder_type.value}"
            )

        return success

    # ==========================================
    # Validation Methods
    # ==========================================

    async def validate_folder_access(
        self,
        folder_id: str,
        workspace_id: str,
    ) -> bool:
        """
        Validate that folder belongs to the workspace.

        Args:
            folder_id: Folder UUID
            workspace_id: Workspace UUID (from user context)

        Returns:
            True if folder belongs to workspace
        """
        folder = await self._repo.get_by_id(folder_id)
        if not folder:
            return False
        return folder.workspace_id == workspace_id

    async def exists(self, folder_id: str) -> bool:
        """
        Check if a folder exists.

        Args:
            folder_id: Folder UUID

        Returns:
            True if folder exists
        """
        return await self._repo.exists(folder_id)

    async def get_item_count(self, folder_id: str) -> int:
        """
        Get the number of items in a folder.

        Args:
            folder_id: Folder UUID

        Returns:
            Number of items (projects or assets) in the folder
        """
        return await self._repo.count_items(folder_id)
