"""Generation History Service - Generation history management.

@module domains.generation.history_service
@version 3.1.0

Service for managing user generation history with complete DDD architecture.
Handles queries, updates, and deletions with ownership verification.

Changes:
- v3.1.0: WS-4 - Depend on IGenerationHistoryRepository interface instead of raw db_client
"""

import logging
from typing import Dict, List, Any

from domains.generation.repository import IGenerationHistoryRepository
from infrastructure.logging.activity_logger import log_activity_async

logger = logging.getLogger(__name__)


# ==========================================
# Custom Exceptions
# ==========================================

class GenerationNotFoundException(Exception):
    """Raised when generation is not found or user doesn't have access."""
    pass


# ==========================================
# GenerationHistoryService
# ==========================================

class GenerationHistoryService:
    """
    Service for generation history management.

    Handles query, update, and deletion operations for user generation history.

    Responsibilities:
    - Retrieve generation history with pagination and filtering
    - Update generation properties (e.g., favorite status)
    - Delete single generation with ownership verification
    - Batch delete generations with optional favorite preservation
    - Activity logging for all mutations

    Architecture: API → GenerationHistoryService → IGenerationHistoryRepository

    v3.0.0: Created for DDD compliance (GEN-CRITICAL-1 fix)
    v3.1.0: WS-4 - Depend on IGenerationHistoryRepository interface
    """

    def __init__(self, repository: IGenerationHistoryRepository):
        """
        Initialize GenerationHistoryService.

        Args:
            repository: Generation history repository interface
        """
        self._repo = repository

    # ==========================================
    # Public Methods
    # ==========================================

    async def get_history(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        favorites_only: bool = False,
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get user's generation history with pagination and filtering.

        Args:
            user_id: User ID for ownership filter
            limit: Maximum number of records to return (1-100)
            offset: Number of records to skip
            favorites_only: If True, only return favorited generations

        Returns:
            tuple: (generations, total_count)
                - generations: List of generation records
                - total_count: Total number of matching records

        Example:
            >>> generations, total = await service.get_history("user_123", limit=20, offset=0)
            >>> print(f"Found {total} generations, showing {len(generations)}")
        """
        return await self._repo.get_history(
            user_id=user_id,
            limit=limit,
            offset=offset,
            favorites_only=favorites_only,
        )

    async def update_generation(
        self,
        user_id: str,
        generation_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update generation properties.

        Args:
            user_id: User ID for ownership verification
            generation_id: Generation ID to update
            updates: Dictionary of fields to update (e.g., {"is_favorited": True})

        Returns:
            Dict: Updated generation record

        Raises:
            GenerationNotFoundException: If generation not found or user doesn't own it

        Example:
            >>> result = await service.update_generation(
            ...     "user_123",
            ...     "gen_abc",
            ...     {"is_favorited": True}
            ... )
        """
        result = await self._repo.update_generation(
            user_id=user_id,
            generation_id=generation_id,
            updates=updates,
        )

        if not result:
            raise GenerationNotFoundException("Generation not found")

        return result

    async def delete_generation(
        self,
        user_id: str,
        generation_id: str,
    ) -> str:
        """
        Delete a single generation.

        Args:
            user_id: User ID for ownership verification
            generation_id: Generation ID to delete

        Returns:
            str: Deleted generation ID

        Raises:
            GenerationNotFoundException: If generation not found or user doesn't own it

        Example:
            >>> deleted_id = await service.delete_generation("user_123", "gen_abc")
            >>> print(f"Deleted: {deleted_id}")
        """
        deleted = await self._repo.delete_generation(
            user_id=user_id,
            generation_id=generation_id,
        )

        if not deleted:
            raise GenerationNotFoundException("Generation not found")

        # Log activity
        await log_activity_async(user_id, "delete_generation", {"generation_id": generation_id})

        return generation_id

    async def batch_delete(
        self,
        user_id: str,
        keep_favorites: bool = True,
    ) -> int:
        """
        Batch delete generations, optionally keeping favorites.

        Args:
            user_id: User ID for ownership verification
            keep_favorites: If True, preserve favorited generations

        Returns:
            int: Number of deleted generations

        Example:
            >>> deleted_count = await service.batch_delete("user_123", keep_favorites=True)
            >>> print(f"Deleted {deleted_count} generations")
        """
        deleted_count = await self._repo.batch_delete(
            user_id=user_id,
            keep_favorites=keep_favorites,
        )

        # Log activity
        await log_activity_async(user_id, "batch_delete_generations", {
            "keep_favorites": keep_favorites,
            "deleted_count": deleted_count,
        })

        return deleted_count
