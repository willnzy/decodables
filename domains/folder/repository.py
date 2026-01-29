"""
Folder Repository Interface

Defines the contract for Folder data access.

@module domains.folder.repository
@version 1.0.0 (created for v3.33 Workspace + Tag Phase 2.6)
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

from .entities import Folder, FolderType


class IFolderRepository(ABC):
    """
    Abstract repository interface for Folder domain.

    Provides CRUD operations for folders within a workspace.
    """

    @abstractmethod
    async def get_by_id(self, folder_id: str) -> Optional[Folder]:
        """
        Get folder by ID.

        Args:
            folder_id: Folder UUID

        Returns:
            Folder entity or None if not found
        """
        pass

    @abstractmethod
    async def get_by_workspace(
        self,
        workspace_id: str,
        folder_type: FolderType,
    ) -> List[Folder]:
        """
        Get all folders of a specific type in a workspace.

        Args:
            workspace_id: Workspace UUID
            folder_type: Type of folder (project or asset)

        Returns:
            List of Folder entities ordered by sort_order
        """
        pass

    @abstractmethod
    async def get_by_workspace_and_name(
        self,
        workspace_id: str,
        folder_type: FolderType,
        name: str,
    ) -> Optional[Folder]:
        """
        Get folder by workspace, type, and name.

        Useful for checking uniqueness constraint.

        Args:
            workspace_id: Workspace UUID
            folder_type: Type of folder
            name: Folder name

        Returns:
            Folder entity or None if not found
        """
        pass

    @abstractmethod
    async def create(self, folder: Folder) -> Folder:
        """
        Create a new folder.

        Args:
            folder: Folder entity to create

        Returns:
            Created Folder with ID populated

        Raises:
            ValueError: If folder name already exists in workspace/type
        """
        pass

    @abstractmethod
    async def update(self, folder: Folder) -> Folder:
        """
        Update an existing folder.

        Args:
            folder: Folder entity with updated fields

        Returns:
            Updated Folder entity
        """
        pass

    @abstractmethod
    async def update_partial(self, folder_id: str, data: dict) -> Optional[Folder]:
        """
        Partially update a folder.

        Args:
            folder_id: Folder UUID
            data: Dictionary of fields to update

        Returns:
            Updated Folder entity or None if not found
        """
        pass

    @abstractmethod
    async def delete(self, folder_id: str) -> bool:
        """
        Delete a folder.

        Note: Items in the folder will have folder_id set to NULL
        due to ON DELETE SET NULL constraint.

        Args:
            folder_id: Folder UUID

        Returns:
            True if deleted successfully
        """
        pass

    @abstractmethod
    async def exists(self, folder_id: str) -> bool:
        """
        Check if a folder exists.

        Args:
            folder_id: Folder UUID

        Returns:
            True if folder exists
        """
        pass

    @abstractmethod
    async def count_items(self, folder_id: str, workspace_id: Optional[str] = None) -> int:
        """
        Count items (projects or assets) in a folder.

        Args:
            folder_id: Folder UUID
            workspace_id: Workspace UUID for data isolation filtering

        Returns:
            Number of items in the folder
        """
        pass

    @abstractmethod
    async def count_items_by_type(
        self,
        folder_id: str,
        folder_type: FolderType,
        user_id: str,
        workspace_id: Optional[str] = None,
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
            workspace_id: Workspace UUID for data isolation filtering

        Returns:
            Dict with 'total', 'bought_count', 'selling_count'
        """
        pass

    @abstractmethod
    async def get_preview_items(
        self,
        folder_id: str,
        folder_type: FolderType,
        limit: int = 4,
        workspace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get preview items (thumbnails) for a folder.

        Returns up to `limit` items with id and thumbnail_url,
        ordered by most recently updated.

        Args:
            folder_id: Folder UUID
            folder_type: Type of folder (project or asset)
            limit: Max number of preview items (default: 4)
            workspace_id: Workspace UUID for data isolation filtering

        Returns:
            List of dicts with 'id' and 'thumbnail_url' keys
        """
        pass

    @abstractmethod
    async def reorder(
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
        pass
