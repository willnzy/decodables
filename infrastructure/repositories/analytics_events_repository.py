"""
Analytics Events Repository - Data access for analytics events batch insertion.

@module infrastructure.repositories.analytics_events_repository
@version 2.0.0 (AsyncClient Migration - Phase 6)

Handles batch insertion of analytics events to multiple tables:
- user_events
- analytics_events
- activity_logs

v2.0 Changes:
- Removed run_in_threadpool wrappers
- All database calls now use native async/await with AsyncClient
"""

import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class SupabaseAnalyticsEventsRepository:
    """
    Repository for analytics events batch insertion.

    Provides methods to insert events into user_events, analytics_events,
    and activity_logs tables in batch operations.
    """

    def __init__(self, supabase_client):
        """
        Initialize repository with Supabase client.

        Args:
            supabase_client: Supabase client instance
        """
        self.client = supabase_client

    async def batch_insert_user_events(
        self, event_rows: List[Dict[str, Any]]
    ) -> int:
        """
        Batch insert events to user_events table.

        Args:
            event_rows: List of event dictionaries

        Returns:
            Number of events successfully inserted
        """
        if not event_rows:
            return 0

        try:
            await self.client.table("user_events").insert(event_rows).execute()
            return len(event_rows)
        except Exception as e:
            logger.warning(
                f"[AnalyticsEventsRepo] Failed to batch insert {len(event_rows)} "
                f"events to user_events: {e}"
            )
            return 0

    async def batch_insert_analytics_events(
        self, event_rows: List[Dict[str, Any]]
    ) -> int:
        """
        Batch insert events to analytics_events table.

        Args:
            event_rows: List of event dictionaries

        Returns:
            Number of events successfully inserted
        """
        if not event_rows:
            return 0

        try:
            await self.client.table("analytics_events").insert(event_rows).execute()
            return len(event_rows)
        except Exception as e:
            logger.warning(
                f"[AnalyticsEventsRepo] Failed to batch insert {len(event_rows)} "
                f"events to analytics_events: {e}"
            )
            return 0

    async def batch_insert_activity_logs(
        self, activity_rows: List[Dict[str, Any]]
    ) -> int:
        """
        Batch insert events to activity_logs table.

        Args:
            activity_rows: List of activity dictionaries

        Returns:
            Number of activities successfully inserted
        """
        if not activity_rows:
            return 0

        try:
            await self.client.table("activity_logs").insert(activity_rows).execute()
            return len(activity_rows)
        except Exception as e:
            logger.warning(
                f"[AnalyticsEventsRepo] Failed to batch insert {len(activity_rows)} "
                f"events to activity_logs: {e}"
            )
            return 0

    async def batch_insert_all(
        self,
        user_event_rows: List[Dict[str, Any]],
        analytics_event_rows: List[Dict[str, Any]],
        activity_rows: List[Dict[str, Any]]
    ) -> Tuple[int, int, int]:
        """
        Batch insert events to all three tables.

        Args:
            user_event_rows: List of user events
            analytics_event_rows: List of analytics events
            activity_rows: List of activity logs

        Returns:
            Tuple of (user_events_inserted, analytics_events_inserted, activity_logs_inserted)
        """
        user_events_inserted = await self.batch_insert_user_events(user_event_rows)
        analytics_events_inserted = await self.batch_insert_analytics_events(analytics_event_rows)
        activity_logs_inserted = await self.batch_insert_activity_logs(activity_rows)

        return user_events_inserted, analytics_events_inserted, activity_logs_inserted
