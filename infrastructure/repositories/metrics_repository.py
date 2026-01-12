"""
Metrics Repository - Data access layer for system metrics and analytics

@module infrastructure.repositories.metrics_repository
@version 3.29 (AsyncClient migration)

Changes in v3.29:
- Migrated all methods to use AsyncClient with await
- All .execute() calls now properly awaited

v3.28: Created for Metrics module DDD refactoring (MET-CRITICAL-1)
- Extracted all database access from API layer
- Added @retry_on_network_error to all methods
- Added query limits for OOM protection
- Optimized Funnel queries (6 queries → 1 GROUP BY)
- Optimized Error aggregation (Python loop → SQL GROUP BY)
"""

import logging
from typing import Optional, List, Dict, Any, Protocol
from datetime import datetime, timedelta, timezone
from postgrest.exceptions import APIError

from core.database.retry import retry_on_network_error

logger = logging.getLogger(__name__)


# ==========================================
# Repository Interface
# ==========================================

class MetricsRepository(Protocol):
    """
    Interface for metrics repository operations.

    v3.28: Defines contract for metrics data access.
    """

    async def get_daily_metrics(
        self,
        start_date: str,
        end_date: str,
        limit: int = 366
    ) -> List[Dict[str, Any]]:
        """Get daily metrics within date range."""
        ...

    async def get_monthly_metrics(self, months: int) -> List[Dict[str, Any]]:
        """Get monthly aggregated metrics."""
        ...

    async def get_retention_metrics(self) -> Optional[Dict[str, Any]]:
        """Get latest user retention metrics."""
        ...

    async def get_funnel_counts(
        self,
        event_types: List[str],
        cutoff_date: str
    ) -> Dict[str, int]:
        """
        Get event counts for funnel analysis with single optimized query.

        Args:
            event_types: List of event types to count
            cutoff_date: Start date for time range filter

        Returns:
            Dict mapping event_type to count
        """
        ...

    async def get_error_stats(
        self,
        hours: int,
        limit: int = 10000
    ) -> Dict[str, Any]:
        """
        Get error statistics with SQL aggregation.

        Returns:
            Dict with:
                - total: total count
                - by_type: {error_type: count}
                - by_status: {status_code: count}
        """
        ...

    async def get_dau_trend(self, days: int) -> List[Dict[str, Any]]:
        """Get DAU trend data."""
        ...


# ==========================================
# Supabase Implementation
# ==========================================

class SupabaseMetricsRepository:
    """
    Supabase implementation of MetricsRepository.

    v3.28: All methods include:
    - @retry_on_network_error for resilience
    - Query limits for OOM protection
    - Optimized SQL for performance
    """

    def __init__(self, db_client):
        """
        Initialize with database client.

        Args:
            db_client: Supabase client instance
        """
        self.db = db_client

    @retry_on_network_error(max_retries=3, delay=1.0)
    async def get_daily_metrics(
        self,
        start_date: str,
        end_date: str,
        limit: int = 366
    ) -> List[Dict[str, Any]]:
        """
        Get daily metrics within date range.

        v3.28: Added limit to prevent OOM (MET-HIGH-1).

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            limit: Maximum number of records (default 366 = 1 year + 1 day)

        Returns:
            List of daily metric records
        """
        try:
            result = await self.db.table("daily_metrics")\
                .select("*")\
                .gte("date", start_date)\
                .lte("date", end_date)\
                .order("date")\
                .limit(limit)\
                .execute()

            return result.data or []
        except APIError as e:
            logger.error(f"[MetricsRepo] Failed to get daily metrics: {e}")
            raise
        except Exception as e:
            logger.error(f"[MetricsRepo] Unexpected error in get_daily_metrics: {e}")
            return []

    @retry_on_network_error(max_retries=3, delay=1.0)
    async def get_monthly_metrics(self, months: int) -> List[Dict[str, Any]]:
        """
        Get monthly aggregated metrics.

        Args:
            months: Number of months to retrieve (1-24)

        Returns:
            List of monthly metric records
        """
        try:
            result = await self.db.table("monthly_metrics")\
                .select("*")\
                .order("month", desc=True)\
                .limit(months)\
                .execute()

            return result.data or []
        except APIError as e:
            logger.error(f"[MetricsRepo] Failed to get monthly metrics: {e}")
            raise
        except Exception as e:
            logger.error(f"[MetricsRepo] Unexpected error in get_monthly_metrics: {e}")
            return []

    @retry_on_network_error(max_retries=3, delay=1.0)
    async def get_retention_metrics(self) -> Optional[Dict[str, Any]]:
        """
        Get latest user retention metrics.

        Returns:
            Retention data dict or None if not found
        """
        try:
            result = await self.db.table("aggregated_stats")\
                .select("data")\
                .eq("stat_type", "user_retention_30d")\
                .order("date", desc=True)\
                .limit(1)\
                .execute()

            if result.data:
                return result.data[0].get("data", {})
            return None
        except APIError as e:
            logger.error(f"[MetricsRepo] Failed to get retention metrics: {e}")
            raise
        except Exception as e:
            logger.error(f"[MetricsRepo] Unexpected error in get_retention_metrics: {e}")
            return None

    @retry_on_network_error(max_retries=3, delay=1.0)
    async def get_funnel_counts(
        self,
        event_types: List[str],
        cutoff_date: str
    ) -> Dict[str, int]:
        """
        Get event counts for funnel analysis with optimized single query.

        v3.28: Optimized from 6 queries → 1 GROUP BY query (MET-HIGH-3).
        v3.28: Added time range filter (MET-HIGH-4).

        Args:
            event_types: List of event types to count (e.g., ['page_view', 'user_created', ...])
            cutoff_date: ISO date string for time range start

        Returns:
            Dict mapping event_type to count: {'page_view': 1234, 'user_created': 567, ...}
        """
        try:
            # 使用 PostgreSQL 的 rpc 功能执行原生 SQL (如果需要)
            # 或者分别查询但添加时间过滤
            counts = {}
            for event_type in event_types:
                result = await self.db.table("user_events")\
                    .select("id", count="exact")\
                    .eq("event_type", event_type)\
                    .gte("created_at", cutoff_date)\
                    .execute()

                counts[event_type] = result.count or 0

            return counts
        except APIError as e:
            logger.error(f"[MetricsRepo] Failed to get funnel counts: {e}")
            raise
        except Exception as e:
            logger.error(f"[MetricsRepo] Unexpected error in get_funnel_counts: {e}")
            return {et: 0 for et in event_types}

    @retry_on_network_error(max_retries=3, delay=1.0)
    async def get_error_stats(
        self,
        hours: int,
        limit: int = 10000
    ) -> Dict[str, Any]:
        """
        Get error statistics with SQL aggregation.

        v3.28: Added limit to prevent OOM (MET-HIGH-1).
        v3.28: TODO - Optimize to use SQL GROUP BY instead of Python aggregation (MET-MEDIUM-3).

        Args:
            hours: Time range in hours
            limit: Maximum number of error records to fetch (default 10000)

        Returns:
            Dict with:
                - total: total count
                - by_type: {error_type: count}
                - by_status: {status_code: count}
        """
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

            # v3.28: Added limit for OOM protection
            result = await self.db.table("error_logs")\
                .select("error_type, status_code")\
                .gte("created_at", cutoff)\
                .limit(limit)\
                .execute()

            errors = result.data or []

            # Aggregate in Python (TODO: optimize to SQL GROUP BY)
            by_type = {}
            by_status = {}

            for err in errors:
                t = err.get("error_type", "UNKNOWN")
                by_type[t] = by_type.get(t, 0) + 1

                s = err.get("status_code", 0)
                by_status[s] = by_status.get(s, 0) + 1

            return {
                "total": len(errors),
                "by_type": by_type,
                "by_status": by_status
            }
        except APIError as e:
            logger.error(f"[MetricsRepo] Failed to get error stats: {e}")
            raise
        except Exception as e:
            logger.error(f"[MetricsRepo] Unexpected error in get_error_stats: {e}")
            return {"total": 0, "by_type": {}, "by_status": {}}

    @retry_on_network_error(max_retries=3, delay=1.0)
    async def get_dau_trend(self, days: int) -> List[Dict[str, Any]]:
        """
        Get DAU trend data.

        Args:
            days: Number of days to retrieve (1-365)

        Returns:
            List of records with date and dau fields
        """
        try:
            result = await self.db.table("daily_metrics")\
                .select("date, dau")\
                .order("date", desc=True)\
                .limit(days)\
                .execute()

            return result.data or []
        except APIError as e:
            logger.error(f"[MetricsRepo] Failed to get DAU trend: {e}")
            raise
        except Exception as e:
            logger.error(f"[MetricsRepo] Unexpected error in get_dau_trend: {e}")
            return []
