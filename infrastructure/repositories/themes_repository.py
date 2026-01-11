"""Supabase implementation of ThemesRepository.

@module infrastructure.repositories.themes_repository
@version 1.0.0
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class SupabaseThemesRepository:
    """Supabase implementation of ThemesRepository."""

    def __init__(self, supabase_client):
        """
        Initialize with Supabase client.

        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client

    async def list_active_themes(self) -> List[Dict[str, Any]]:
        """
        Get all active themes ordered by priority (descending).

        Returns:
            List of active theme dictionaries

        Raises:
            Exception: If query fails
        """
        try:
            result = self.supabase.table("daily_themes").select("*").eq(
                "is_active", True
            ).order("priority", desc=True).execute()

            if not result.data:
                return []

            return result.data

        except Exception as e:
            logger.error(f"Failed to list active themes: {e}")
            raise
