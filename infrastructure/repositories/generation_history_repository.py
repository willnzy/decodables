"""
Supabase Generation History Repository - Concrete implementation.

@module infrastructure.repositories.generation_history_repository
@version 1.0.0

WS-4: Created to implement IGenerationHistoryRepository interface.
Moves raw db_client.table("user_generations") calls from domain to infrastructure.
"""

import logging
from typing import Dict, List, Any, Optional

from domains.generation.repository import IGenerationHistoryRepository

logger = logging.getLogger(__name__)


class SupabaseGenerationHistoryRepository(IGenerationHistoryRepository):
    """
    Supabase implementation of IGenerationHistoryRepository.

    All user_generations table operations go through this repository.
    """

    def __init__(self, db_client):
        """
        Initialize with AsyncClient.

        Args:
            db_client: Supabase AsyncClient
        """
        self._db = db_client

    async def get_history(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        favorites_only: bool = False,
    ) -> tuple[List[Dict[str, Any]], int]:
        """Get user's generation history with pagination."""
        # Build query
        query = self._db.table("user_generations") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True)

        if favorites_only:
            query = query.eq("is_favorited", True)

        # Get paginated data
        result = await query.range(offset, offset + limit - 1).execute()

        # Get total count with same filters
        count_query = self._db.table("user_generations") \
            .select("id", count="exact") \
            .eq("user_id", user_id)

        if favorites_only:
            count_query = count_query.eq("is_favorited", True)

        count_result = await count_query.execute()

        total_count = count_result.count if count_result.count is not None else len(result.data or [])

        return result.data or [], total_count

    async def insert_generation(
        self,
        record: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Insert a generation history record."""
        try:
            result = await self._db.table("user_generations").insert(record).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.warning(f"Failed to insert generation history: {e}")
            return None

    async def update_generation(
        self,
        user_id: str,
        generation_id: str,
        updates: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Update a generation record with ownership verification."""
        result = await self._db.table("user_generations") \
            .update(updates) \
            .eq("id", generation_id) \
            .eq("user_id", user_id) \
            .execute()

        return result.data[0] if result.data else None

    async def delete_generation(
        self,
        user_id: str,
        generation_id: str,
    ) -> bool:
        """Delete a single generation with ownership verification."""
        result = await self._db.table("user_generations") \
            .delete() \
            .eq("id", generation_id) \
            .eq("user_id", user_id) \
            .execute()

        return bool(result.data)

    async def batch_delete(
        self,
        user_id: str,
        keep_favorites: bool = True,
    ) -> int:
        """Batch delete generations."""
        query = self._db.table("user_generations") \
            .delete() \
            .eq("user_id", user_id)

        if keep_favorites:
            query = query.eq("is_favorited", False)

        result = await query.execute()
        return len(result.data or [])
