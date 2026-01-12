"""Themes Repository Interface.

@module domains.themes.repository
@version 2.1.0

v2.1.0: Added methods for CRUD, review workflow, and batch operations
"""

from datetime import date
from typing import Protocol, List, Dict, Any, Optional, Set


class ThemesRepository(Protocol):
    """Repository interface for holiday themes operations."""

    # ==========================================
    # Read Operations
    # ==========================================

    async def get_by_id(self, theme_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a theme by its ID.

        Args:
            theme_id: Theme unique identifier (UUID)

        Returns:
            Theme dictionary or None if not found
        """
        ...

    async def get_by_date(self, target_date: date) -> Optional[Dict[str, Any]]:
        """
        Get a theme for a specific date.

        Args:
            target_date: The date to look up

        Returns:
            Theme dictionary or None if not found
        """
        ...

    async def list_active_themes(self) -> List[Dict[str, Any]]:
        """
        Get all active themes ordered by priority (descending).

        Returns:
            List of active theme dictionaries
        """
        ...

    async def list_all(
        self,
        offset: int = 0,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        List themes with pagination and filters.

        Args:
            offset: Pagination offset
            limit: Page size
            filters: Optional filters (category, status, review_status, date_from, date_to)

        Returns:
            List of theme dictionaries
        """
        ...

    async def count_all(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count themes matching filters.

        Args:
            filters: Optional filters

        Returns:
            Total count
        """
        ...

    # ==========================================
    # Write Operations
    # ==========================================

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new theme.

        Args:
            data: Theme data dictionary

        Returns:
            Created theme with ID

        Raises:
            Exception: If creation fails
        """
        ...

    async def update(
        self, theme_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing theme.

        Args:
            theme_id: Theme ID to update
            data: Fields to update

        Returns:
            Updated theme or None if not found
        """
        ...

    async def delete(self, theme_id: str) -> bool:
        """
        Soft delete a theme.

        Args:
            theme_id: Theme ID to delete

        Returns:
            True if deleted, False if not found
        """
        ...

    # ==========================================
    # Review Operations (v2.1)
    # ==========================================

    async def list_for_review(
        self,
        filters: Optional[Dict[str, Any]] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        List themes pending review.

        Args:
            filters: Optional filters (review_status)
            offset: Pagination offset
            limit: Page size

        Returns:
            List of themes for review
        """
        ...

    async def count_for_review(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count themes pending review.

        Args:
            filters: Optional filters

        Returns:
            Count of themes
        """
        ...

    async def batch_update_review_status(
        self,
        theme_ids: List[str],
        review_status: str,
        reviewed_by: str,
    ) -> int:
        """
        Batch update review status for multiple themes.

        Args:
            theme_ids: List of theme IDs
            review_status: New review status
            reviewed_by: Admin user ID

        Returns:
            Number of themes updated
        """
        ...

    # ==========================================
    # Statistics Operations (v2.1)
    # ==========================================

    async def get_existing_dates(
        self, start_date: date, end_date: date
    ) -> Set[date]:
        """
        Get dates that already have themes.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Set of dates with existing themes
        """
        ...

    async def get_review_status_stats(
        self, start_date: date, end_date: date
    ) -> Dict[str, int]:
        """
        Get statistics of review statuses in date range.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Dict with counts per review status
        """
        ...
