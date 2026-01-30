"""
Generation Repository Interfaces - Abstract data access for generation domain.

@module domains.generation.repository
@version 1.0.0

Defines repository interfaces (ports) for the generation domain.
Concrete implementations live in infrastructure/repositories/.

WS-4: Created to fix DDD dependency direction violations.
Domain services depend on these interfaces, not concrete implementations.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class IAssetRepository(ABC):
    """
    Repository interface for asset operations used by generation domain.

    Follows the Repository pattern from DDD.
    Infrastructure layer provides the concrete implementation (SupabaseAssetRepository).
    """

    @abstractmethod
    async def save_asset(
        self,
        user_id: str,
        url: str,
        source: str,
        project_id: Optional[str] = None,
        prompt: Optional[str] = None,
        tz: str = "UTC",
        asset_type: str = "image",
        workspace_id: Optional[str] = None,
        folder_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Save a new asset.

        Args:
            user_id: User ID
            url: Asset URL
            source: Asset source (upload, ai_generated, system, marketplace)
            project_id: Optional project ID
            prompt: Optional prompt used to generate
            tz: Timezone string
            asset_type: Asset type (image, text, etc.)
            workspace_id: Optional workspace ID
            folder_id: Optional folder ID

        Returns:
            Saved asset dict or None
        """
        pass


class IGenerationHistoryRepository(ABC):
    """
    Repository interface for generation history operations.

    Follows the Repository pattern from DDD.
    Replaces direct db_client.table("user_generations") calls in domain services.
    """

    @abstractmethod
    async def get_history(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        favorites_only: bool = False,
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get user's generation history with pagination.

        Args:
            user_id: User ID
            limit: Max records (1-100)
            offset: Records to skip
            favorites_only: Filter favorites only

        Returns:
            Tuple of (generations list, total count)
        """
        pass

    @abstractmethod
    async def insert_generation(
        self,
        record: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Insert a generation history record.

        Args:
            record: Generation record data

        Returns:
            Inserted record or None
        """
        pass

    @abstractmethod
    async def update_generation(
        self,
        user_id: str,
        generation_id: str,
        updates: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Update a generation record.

        Args:
            user_id: User ID for ownership verification
            generation_id: Generation ID
            updates: Fields to update

        Returns:
            Updated record or None if not found
        """
        pass

    @abstractmethod
    async def delete_generation(
        self,
        user_id: str,
        generation_id: str,
    ) -> bool:
        """
        Delete a single generation record.

        Args:
            user_id: User ID for ownership verification
            generation_id: Generation ID

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def batch_delete(
        self,
        user_id: str,
        keep_favorites: bool = True,
    ) -> int:
        """
        Batch delete generations.

        Args:
            user_id: User ID
            keep_favorites: If True, preserve favorited generations

        Returns:
            Number of deleted records
        """
        pass
