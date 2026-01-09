"""
Events Repository Implementation - Supabase data access.

@module infrastructure.repositories.events_repository
@version 1.0.0 (created for v3.27 refactor)

Implements IEventsRepository using Supabase PostgreSQL.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
import logging

from domains.events.repository import IEventsRepository
from domains.events.entities import UserEvent, AggregatedStats
from domains.events.constants import MAX_QUERY_LIMIT, DEFAULT_STATS_DAYS
from core.database import get_supabase_client
from core.database.retry import retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseEventsRepository(IEventsRepository):
    """
    Supabase implementation of Events repository.
    """

    def __init__(self, client=None):
        """Initialize repository with Supabase client."""
        self._client = client

    @property
    def client(self):
        """Lazy load Supabase client."""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    @retry_on_network_error()
    async def get_user_events(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get user events with filters and pagination."""
        try:
            query = self.client.table("user_events").select("*", count="exact")

            if user_id:
                query = query.eq("user_id", user_id)
            if event_type:
                query = query.eq("event_type", event_type)
            if start_date:
                query = query.gte("created_at", start_date)
            if end_date:
                query = query.lte("created_at", end_date)

            result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            total = result.count or 0

            return {
                "events": result.data or [],
                "total": total,
                "offset": offset,
                "limit": limit,
                "has_more": (offset + limit) < total
            }

        except Exception as e:
            logger.error(f"[EventsRepository] get_user_events failed: {e}")
            raise

    @retry_on_network_error()
    async def get_event_stats(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        group_by: str = "event_type"
    ) -> Dict[str, int]:
        """
        Get event statistics with grouping support.

        TODO (EVT-MEDIUM-3): Migrate to database-level aggregation (GROUP BY)
        Currently using application-level aggregation for compatibility.
        """
        try:
            if not start_date:
                start_date = (datetime.now(timezone.utc) - timedelta(days=DEFAULT_STATS_DAYS)).isoformat()

            # Select fields based on group_by
            if group_by == "event_type":
                fields = "event_type"
            elif group_by == "user_id":
                fields = "user_id"
            elif group_by in ("date", "hour"):
                fields = "created_at"
            else:
                fields = "event_type"  # Fallback

            # Query with limit to prevent OOM (EVT-HIGH-2 fix)
            query = self.client.table("user_events").select(fields).gte("created_at", start_date).limit(MAX_QUERY_LIMIT)

            if end_date:
                query = query.lte("created_at", end_date)

            result = query.execute()

            # Application-level aggregation
            # TODO: Replace with SQL GROUP BY for better performance
            stats = {}
            for event in (result.data or []):
                if group_by == "event_type":
                    key = event.get("event_type", "unknown")
                elif group_by == "user_id":
                    key = event.get("user_id", "unknown")
                elif group_by == "date":
                    created_at = event.get("created_at", "")
                    key = created_at[:10] if created_at else "unknown"  # YYYY-MM-DD
                elif group_by == "hour":
                    created_at = event.get("created_at", "")
                    key = created_at[:13] if created_at else "unknown"  # YYYY-MM-DDTHH
                else:
                    key = "unknown"

                stats[key] = stats.get(key, 0) + 1

            return stats

        except Exception as e:
            logger.error(f"[EventsRepository] get_event_stats failed: {e}")
            raise

    @retry_on_network_error()
    async def get_aggregated_stats(
        self,
        stat_type: str,
        use_cache: bool = True
    ) -> Optional[AggregatedStats]:
        """Get today's aggregated statistics."""
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            result = self.client.table("aggregated_stats").select("*")\
                .eq("stat_type", stat_type)\
                .eq("date", today)\
                .execute()

            if not result.data:
                return None

            return AggregatedStats.from_dict(result.data[0])

        except Exception as e:
            logger.error(f"[EventsRepository] get_aggregated_stats failed: {e}")
            raise

    @retry_on_network_error()
    async def get_aggregated_stats_range(
        self,
        stat_type: str,
        days: int = 30
    ) -> List[AggregatedStats]:
        """Get aggregated statistics for a date range."""
        try:
            start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
            result = self.client.table("aggregated_stats").select("*")\
                .eq("stat_type", stat_type)\
                .gte("date", start)\
                .order("date", desc=True)\
                .execute()

            return [AggregatedStats.from_dict(row) for row in (result.data or [])]

        except Exception as e:
            logger.error(f"[EventsRepository] get_aggregated_stats_range failed: {e}")
            raise

    @retry_on_network_error()
    async def create_event(self, event: UserEvent) -> UserEvent:
        """Create a new user event."""
        try:
            data = {
                "user_id": event.user_id,
                "event_type": event.event_type,
                "event_data": event.event_data,
                "session_id": event.session_id,
                "ip_address": event.ip_address,
                "user_agent": event.user_agent,
            }

            result = self.client.table("user_events").insert(data).execute()

            if result.data:
                return UserEvent.from_dict(result.data[0])

            return event

        except Exception as e:
            logger.error(f"[EventsRepository] create_event failed: {e}")
            raise

    @retry_on_network_error()
    async def delete_old_events(self, days: int = 90) -> int:
        """Delete events older than specified days."""
        try:
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

            result = self.client.table("user_events").delete()\
                .lt("created_at", cutoff_date)\
                .execute()

            return len(result.data) if result.data else 0

        except Exception as e:
            logger.error(f"[EventsRepository] delete_old_events failed: {e}")
            raise
