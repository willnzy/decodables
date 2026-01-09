"""
Error Logs Repository - Data access layer for error logs management.

@module infrastructure.repositories.error_logs_repository
@version 1.0.0

This module provides database access methods for error logs,
following DDD architecture and Repository pattern.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from core.database import retry_on_network_error


class ErrorLogsRepository(ABC):
    """Abstract interface for error logs data access."""

    @abstractmethod
    async def get_error_logs(
        self,
        error_level: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get error logs with filters and pagination."""
        pass

    @abstractmethod
    async def get_error_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get error statistics for the last N hours."""
        pass

    @abstractmethod
    async def get_error_logs_for_export(
        self,
        error_level: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100000
    ) -> List[Dict[str, Any]]:
        """Get error logs for export (no pagination)."""
        pass


class SupabaseErrorLogsRepository(ErrorLogsRepository):
    """Supabase implementation of ErrorLogsRepository."""

    def __init__(self, client):
        """
        Initialize repository with Supabase client.

        Args:
            client: Supabase client instance
        """
        self.client = client

    @retry_on_network_error()
    async def get_error_logs(
        self,
        error_level: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get error logs with filters and pagination.

        Args:
            error_level: Filter by error level (error, warning, critical, etc.)
            start_date: Start date for filtering (ISO format)
            end_date: End date for filtering (ISO format)
            offset: Pagination offset
            limit: Maximum number of logs to return (1-100)

        Returns:
            Dict with logs, total, offset, limit, has_more
        """
        query = self.client.table("error_logs").select("*", count="exact")

        if error_level:
            query = query.eq("level", error_level)
        if start_date:
            query = query.gte("created_at", start_date)
        if end_date:
            query = query.lte("created_at", end_date)

        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        total = result.count or 0

        return {
            "logs": result.data or [],
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": (offset + limit) < total
        }

    @retry_on_network_error()
    async def get_error_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get error statistics for the last N hours.

        Args:
            hours: Number of hours to look back (1-168)

        Returns:
            Dict with error statistics:
            - total_errors: Total count
            - by_level: Distribution by error level
            - by_type: Distribution by error type
            - by_hour: Time series by hour
            - trend: Time series as list
        """
        start_date = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        # LOG-HIGH-1: Added .limit(100000) to prevent OOM
        result = self.client.table("error_logs").select(
            "level, error_type, created_at"
        ).gte("created_at", start_date).limit(100000).execute()

        # Aggregate statistics in memory
        stats = {
            "total_errors": len(result.data or []),
            "by_level": {},
            "by_type": {},
            "by_hour": {},
            "trend": []
        }

        for error in (result.data or []):
            level = error.get("level", "unknown")
            error_type = error.get("error_type", "unknown")
            created_at = error.get("created_at", "")

            # Count by level
            stats["by_level"][level] = stats["by_level"].get(level, 0) + 1

            # Count by type
            stats["by_type"][error_type] = stats["by_type"].get(error_type, 0) + 1

            # Count by hour
            if created_at:
                hour = created_at[:13]  # YYYY-MM-DDTHH
                stats["by_hour"][hour] = stats["by_hour"].get(hour, 0) + 1

        # Convert by_hour to trend list (sorted by time)
        stats["trend"] = [
            {"hour": k, "count": v}
            for k, v in sorted(stats["by_hour"].items())
        ]

        return stats

    @retry_on_network_error()
    async def get_error_logs_for_export(
        self,
        error_level: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100000
    ) -> List[Dict[str, Any]]:
        """
        Get error logs for export (no pagination).

        Used by export endpoints to retrieve large datasets.
        Limited to prevent OOM.

        Args:
            error_level: Filter by error level
            start_date: Start date for filtering (ISO format)
            end_date: End date for filtering (ISO format)
            limit: Maximum number of logs (default 100000)

        Returns:
            List of error log entries
        """
        query = self.client.table("error_logs").select("*")

        if error_level:
            query = query.eq("level", error_level)
        if start_date:
            query = query.gte("created_at", start_date)
        if end_date:
            query = query.lte("created_at", end_date)

        result = query.order("created_at", desc=True).limit(limit).execute()
        return result.data or []
