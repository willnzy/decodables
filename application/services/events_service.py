"""
Events Application Service

Use case orchestration for Events domain.

@module application.services.events_service
@version 1.0.0 (created for v3.27 refactor)

This service orchestrates use cases by coordinating between:
- Domain Service (business rules)
- Repository (data access)
- External services (if needed)
"""

from typing import Optional, List, Dict, Any
import logging

from domains.events import (
    IEventsRepository,
    EventsDomainService,
    UserEvent,
    EventStats,
    AggregatedStats,
    VALID_GROUP_BY,
    VALID_STAT_TYPES,
    MAX_LIMIT,
    DEFAULT_RANGE_DAYS,
)

logger = logging.getLogger(__name__)


# Phase 4: Audit logging helper (v2.0 AsyncClient)
async def _log_admin_operation(
    admin_id: str,
    operation_type: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log admin operation to admin_operations table.

    v2.0: Uses AsyncClient instead of sync client.

    Args:
        admin_id: Admin user ID
        operation_type: Type of operation (e.g., "get_user_events", "get_event_stats")
        details: Additional operation details (filters, parameters, etc.)
    """
    try:
        from core.database import get_async_db_client
        import json

        # Get AsyncClient
        client = await get_async_db_client()

        # Prepare log entry
        log_entry = {
            "admin_id": admin_id,
            "operation_type": operation_type,
            "details": json.dumps(details) if details else None,
            "created_at": "now()"  # PostgreSQL function for server timestamp
        }

        # Write to admin_operations table
        await client.table("admin_operations").insert(log_entry).execute()

        logger.info(
            f"[Audit] Admin {admin_id} performed {operation_type} "
            f"(logged to DB)"
        )
    except Exception as e:
        # Fail gracefully - don't break the main operation if audit logging fails
        logger.error(
            f"[Audit] Failed to log admin operation: {e}. "
            f"Admin: {admin_id}, Operation: {operation_type}"
        )


class EventsService:
    """
    Application service for Events use cases.

    This service orchestrates business operations by coordinating
    domain logic and data access.
    """

    def __init__(self, repository: IEventsRepository):
        """
        Initialize service with repository.

        Args:
            repository: Events repository implementation
        """
        self.repository = repository
        self.domain_service = EventsDomainService()

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
            limit: Page size

        Returns:
            Dict with events, total, offset, limit, has_more

        Raises:
            ValueError: If parameters are invalid
        """
        # Validate dates
        self.domain_service.validate_date_format(start_date, "start_date")
        self.domain_service.validate_date_format(end_date, "end_date")

        # Validate pagination
        self.domain_service.validate_pagination(offset, limit, MAX_LIMIT)

        logger.info(
            f"[EventsService] Getting user events "
            f"(user_id={user_id}, event_type={event_type}, offset={offset}, limit={limit})"
        )

        return await self.repository.get_user_events(
            user_id=user_id,
            event_type=event_type,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            limit=limit
        )

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

        Raises:
            ValueError: If parameters are invalid
        """
        # Validate dates
        self.domain_service.validate_date_format(start_date, "start_date")
        self.domain_service.validate_date_format(end_date, "end_date")

        # Validate group_by
        self.domain_service.validate_group_by(group_by)

        logger.info(
            f"[EventsService] Getting event stats "
            f"(group_by={group_by}, start_date={start_date}, end_date={end_date})"
        )

        return await self.repository.get_event_stats(
            start_date=start_date,
            end_date=end_date,
            group_by=group_by
        )

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

        Raises:
            ValueError: If stat_type is invalid
        """
        # Validate stat_type
        self.domain_service.validate_stat_type(stat_type)

        logger.info(f"[EventsService] Getting aggregated stats (stat_type={stat_type})")

        return await self.repository.get_aggregated_stats(
            stat_type=stat_type,
            use_cache=use_cache
        )

    async def get_aggregated_stats_range(
        self,
        stat_type: str,
        days: int = DEFAULT_RANGE_DAYS
    ) -> List[AggregatedStats]:
        """
        Get aggregated statistics for a date range.

        Args:
            stat_type: Type of statistic
            days: Number of days to fetch (from today backwards)

        Returns:
            List of AggregatedStats entities, ordered by date descending

        Raises:
            ValueError: If parameters are invalid
        """
        # Validate stat_type
        self.domain_service.validate_stat_type(stat_type)

        # Validate days range
        if days < 1:
            raise ValueError("days must be >= 1")

        if days > 90:
            raise ValueError("days must be <= 90")

        logger.info(
            f"[EventsService] Getting aggregated stats range "
            f"(stat_type={stat_type}, days={days})"
        )

        return await self.repository.get_aggregated_stats_range(
            stat_type=stat_type,
            days=days
        )

    async def create_event(self, event: UserEvent) -> UserEvent:
        """
        Create a new user event.

        Args:
            event: UserEvent entity to create

        Returns:
            Created UserEvent with ID populated

        Raises:
            ValueError: If event is invalid
        """
        # Validate event
        self.domain_service.validate_event(event)

        # Sanitize event data
        event.event_data = self.domain_service.sanitize_event_data(event.event_data)

        logger.info(
            f"[EventsService] Creating event "
            f"(user_id={event.user_id}, event_type={event.event_type})"
        )

        return await self.repository.create_event(event)

    async def delete_old_events(self, days: int = 90) -> int:
        """
        Delete events older than specified days.

        Args:
            days: Number of days to retain

        Returns:
            Number of events deleted

        Raises:
            ValueError: If days is invalid
        """
        if days < 1:
            raise ValueError("days must be >= 1")

        logger.info(f"[EventsService] Deleting events older than {days} days")

        return await self.repository.delete_old_events(days=days)
