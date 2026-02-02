"""
Analytics Events Repository - Data access for analytics events batch insertion.

@module infrastructure.repositories.analytics_events_repository
@version 3.0.0 (Complete DDD Implementation)

Implements IAnalyticsRepository interface with full DDD support:
- Single event operations (save, get_by_id, query)
- Batch operations (for frontend events)
- Complete analytics_events, user_events, activity_logs coordination

v3.0 Changes:
- Implements IAnalyticsRepository interface
- Added single event CRUD operations
- Supports AnalyticsEvent entity mapping
- Maintains backward compatibility for batch operations
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

from domains.analytics.repository import IAnalyticsRepository
from domains.analytics.entities import AnalyticsEvent

logger = logging.getLogger(__name__)


class SupabaseAnalyticsEventsRepository(IAnalyticsRepository):
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

    # ========================================================================
    # Single Event Operations (IAnalyticsRepository implementation)
    # ========================================================================
    
    async def save(self, event: AnalyticsEvent) -> None:
        """
        Save a single analytics event.
        
        Args:
            event: AnalyticsEvent entity to save
        """
        try:
            row = event.to_dict()
            await self.client.table("analytics_events").insert(row).execute()
            logger.debug(f"[AnalyticsRepo] Saved event: {event.event_name} (id={event.id})")
        except Exception as e:
            logger.error(
                f"[AnalyticsRepo] Failed to save event {event.event_name}: {e}",
                exc_info=True
            )
            raise
    
    async def save_batch(self, events: List[AnalyticsEvent]) -> int:
        """
        Save multiple analytics events in batch.
        
        Args:
            events: List of AnalyticsEvent entities
            
        Returns:
            Number of events successfully saved
        """
        if not events:
            return 0
        
        try:
            rows = [event.to_dict() for event in events]
            await self.client.table("analytics_events").insert(rows).execute()
            logger.info(f"[AnalyticsRepo] Batch saved {len(events)} events")
            return len(events)
        except Exception as e:
            logger.error(
                f"[AnalyticsRepo] Failed to batch save {len(events)} events: {e}",
                exc_info=True
            )
            return 0
    
    async def get_by_id(self, event_id: str) -> Optional[AnalyticsEvent]:
        """
        Get an analytics event by ID.
        
        Args:
            event_id: Event ID (UUID or custom ID)
            
        Returns:
            AnalyticsEvent if found, None otherwise
        """
        try:
            # Sanitize event_id: strip PostgREST structural chars to prevent filter injection
            safe_id = str(event_id)
            for ch in (",", ".", "(", ")"):
                safe_id = safe_id.replace(ch, "")
            result = await self.client.table("analytics_events")\
                .select('*')\
                .or_(f'id.eq.{safe_id},event_id.eq.{safe_id}')\
                .limit(1)\
                .execute()
            
            if result.data:
                return AnalyticsEvent.from_dict(result.data[0])
            return None
        except Exception as e:
            logger.error(f"[AnalyticsRepo] Failed to get event by id {event_id}: {e}")
            return None
    
    async def get_user_events(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        event_types: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[AnalyticsEvent], int]:
        """
        Get analytics events for a specific user.
        
        Args:
            user_id: User ID
            start_date: Start date for query
            end_date: End date for query
            event_types: Optional list of event types to filter
            limit: Maximum number of events to return
            offset: Number of events to skip
            
        Returns:
            Tuple of (events, total_count)
        """
        try:
            # Build query
            query = self.client.table("analytics_events")\
                .select('*', count='exact')\
                .eq('user_id', user_id)\
                .gte('created_at', start_date.isoformat())\
                .lte('created_at', end_date.isoformat())
            
            # Add event_types filter if provided
            if event_types:
                query = query.in_('event_type', event_types)
            
            # Execute query with pagination
            result = await query\
                .order('created_at', desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            events = [AnalyticsEvent.from_dict(row) for row in result.data]
            total_count = result.count or 0
            
            return events, total_count
        except Exception as e:
            logger.error(f"[AnalyticsRepo] Failed to get user events: {e}")
            return [], 0
    
    async def count_events(
        self,
        event_type: str,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[str] = None
    ) -> int:
        """
        Count analytics events by type and date range.
        
        Args:
            event_type: Event type to count
            start_date: Start date for query
            end_date: End date for query
            user_id: Optional user ID filter
            
        Returns:
            Number of events
        """
        try:
            query = self.client.table("analytics_events")\
                .select('id', count='exact')\
                .eq('event_type', event_type)\
                .gte('created_at', start_date.isoformat())\
                .lte('created_at', end_date.isoformat())
            
            if user_id:
                query = query.eq('user_id', user_id)
            
            result = await query.execute()
            return result.count or 0
        except Exception as e:
            logger.error(f"[AnalyticsRepo] Failed to count events: {e}")
            return 0
