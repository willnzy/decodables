"""
Events Repository Interface

Defines the contract for Events data access.

@module domains.events.repository
@version 1.0.0 (created for v3.27 refactor)
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from .entities import UserEvent, EventStats, AggregatedStats


class IEventsRepository(ABC):
    """
    Abstract repository interface for Events domain.

    This interface defines the contract for all Events data access operations.
    Implementations should handle database-specific logic.
    """

    @abstractmethod
    async def get_user_events(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get user events with filters and pagination.

        Args:
            user_id: Filter by user ID
            event_type: Filter by event type
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            offset: Pagination offset
            limit: Maximum number of events to return

        Returns:
            Dict with events, total, offset, limit, has_more
        """
        pass

    @abstractmethod
    async def get_event_stats(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        group_by: str = "event_type"
    ) -> Dict[str, int]:
        """
        Get event statistics with grouping support.

        Args:
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            group_by: Group by field (event_type, user_id, date, hour)

        Returns:
            Dict mapping group keys to counts
        """
        pass

    @abstractmethod
    async def get_aggregated_stats(
        self,
        stat_type: str,
        use_cache: bool = True
    ) -> Optional[AggregatedStats]:
        """
        Get today's aggregated statistics.

        Args:
            stat_type: Type of statistic (daily_active_users, etc.)
            use_cache: Whether to use cached results

        Returns:
            AggregatedStats entity or None if not found
        """
        pass

    @abstractmethod
    async def get_aggregated_stats_range(
        self,
        stat_type: str,
        days: int = 30
    ) -> List[AggregatedStats]:
        """
        Get aggregated statistics for a date range.

        Args:
            stat_type: Type of statistic
            days: Number of days to fetch (from today backwards)

        Returns:
            List of AggregatedStats entities, ordered by date descending
        """
        pass

    @abstractmethod
    async def create_event(self, event: UserEvent) -> UserEvent:
        """
        Create a new user event.

        Args:
            event: UserEvent entity to create

        Returns:
            Created UserEvent with ID populated
        """
        pass

    @abstractmethod
    async def delete_old_events(self, days: int = 90) -> int:
        """
        Delete events older than specified days.

        Args:
            days: Number of days to retain

        Returns:
            Number of events deleted
        """
        pass
