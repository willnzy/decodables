"""
Admin Metrics Service - Admin-specific metrics and analytics operations.

@module domains.admin.admin_metrics_service
@version 1.0.0

This service encapsulates admin-specific metrics operations:
- Daily/monthly metrics
- Retention metrics
- Funnel metrics
- Error metrics
- DAU trend

WHY separate service?
- Encapsulates complex metrics calculation logic
- Decouples API layer from repository implementations
- Provides unified interface for all metrics operations
- Supports future caching and optimization

Architecture: API → Container → Service → Repository
"""

import logging
from typing import Dict, List, Optional, Protocol, runtime_checkable
from datetime import date, datetime, timedelta, timezone

logger = logging.getLogger(__name__)


# =============================================================================
# Repository Protocol (DIP compliance)
# =============================================================================

@runtime_checkable
class MetricsRepositoryProtocol(Protocol):
    """Protocol for metrics repository operations."""
    async def get_daily_metrics(self, start_date: str, end_date: str) -> List[Dict]: ...
    async def get_monthly_metrics(self, months: int) -> List[Dict]: ...
    async def get_retention_metrics(self) -> Optional[Dict]: ...
    async def get_funnel_counts(self, event_types: List[str], cutoff_date: str) -> Dict[str, int]: ...
    async def get_error_stats(self, hours: int) -> Dict: ...
    async def get_dau_trend(self, days: int) -> List[Dict]: ...


# =============================================================================
# Constants
# =============================================================================

# Valid period values for funnel
VALID_PERIODS = {"7d", "14d", "30d", "60d", "90d"}

# Period to days mapping
PERIOD_TO_DAYS = {
    "7d": 7,
    "14d": 14,
    "30d": 30,
    "60d": 60,
    "90d": 90,
}

# Funnel event types
FUNNEL_EVENT_TYPES = [
    "page_view",
    "user_created",
    "project_create",
    "ai_generate",
    "download_pdf",
    "payment_success",
]

# Funnel step names
FUNNEL_STEP_NAMES = [
    "visitors",
    "signups",
    "first_project",
    "first_generation",
    "first_export",
    "payment",
]


class AdminMetricsService:
    """
    Admin Metrics Service.

    Handles all admin-specific metrics operations.
    Encapsulates metrics calculation and aggregation logic.
    """

    def __init__(self, metrics_repo: MetricsRepositoryProtocol):
        """
        Initialize Admin Metrics Service with repository dependency.

        WHY interface injection?
        - Dependency Inversion Principle (DIP)
        - Easy mocking for tests
        - Decouples from infrastructure

        Args:
            metrics_repo: Metrics repository
        """
        self._metrics_repo = metrics_repo

    # =========================================================================
    # Daily Metrics
    # =========================================================================

    async def get_daily_metrics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        Get daily metrics for dashboard.

        Args:
            start_date: Start date (defaults to 30 days ago)
            end_date: End date (defaults to today)

        Returns:
            Dict with metrics list, start_date, end_date
        """
        if not start_date:
            start_date = (date.today() - timedelta(days=30)).isoformat()
        if not end_date:
            end_date = date.today().isoformat()

        metrics_data = await self._metrics_repo.get_daily_metrics(start_date, end_date)
        return {
            "metrics": metrics_data,
            "start_date": start_date,
            "end_date": end_date
        }

    # =========================================================================
    # Monthly Metrics
    # =========================================================================

    async def get_monthly_metrics(self, months: int = 6) -> Dict:
        """
        Get monthly aggregated metrics.

        Args:
            months: Number of months (1-24)

        Returns:
            Dict with metrics list and months
        """
        metrics_data = await self._metrics_repo.get_monthly_metrics(months)
        return {
            "metrics": metrics_data,
            "months": months
        }

    # =========================================================================
    # Retention Metrics
    # =========================================================================

    async def get_retention_metrics(self) -> Dict:
        """
        Get user retention metrics.

        Returns:
            Dict with retention data or empty dict
        """
        data = await self._metrics_repo.get_retention_metrics()
        return data if data else {}

    # =========================================================================
    # Funnel Metrics
    # =========================================================================

    async def get_funnel_metrics(self, period: str = "30d") -> Dict:
        """
        Get conversion funnel metrics.

        Args:
            period: Time period (7d, 14d, 30d, 60d, 90d)

        Returns:
            Dict with funnel data and period

        Raises:
            ValueError: If period is invalid
        """
        if period not in VALID_PERIODS:
            raise ValueError(f"Invalid period. Must be one of: {', '.join(VALID_PERIODS)}")

        # Calculate time range based on period
        days = PERIOD_TO_DAYS.get(period, 30)
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        # Get counts with time range filter
        counts = await self._metrics_repo.get_funnel_counts(FUNNEL_EVENT_TYPES, cutoff_date)

        # Build funnel data
        funnel_data = []
        for event_type, step_name in zip(FUNNEL_EVENT_TYPES, FUNNEL_STEP_NAMES):
            funnel_data.append({
                "step": step_name,
                "count": counts.get(event_type, 0)
            })

        return {
            "funnel": funnel_data,
            "period": period
        }

    # =========================================================================
    # Error Metrics
    # =========================================================================

    async def get_error_metrics(self, hours: int = 24) -> Dict:
        """
        Get error metrics summary.

        Args:
            hours: Time range in hours (1-168)

        Returns:
            Dict with total, hours, by_type, by_status
        """
        stats = await self._metrics_repo.get_error_stats(hours)
        return {
            "total": stats.get("total", 0),
            "hours": hours,
            "by_type": stats.get("by_type", {}),
            "by_status": stats.get("by_status", {})
        }

    # =========================================================================
    # DAU Trend
    # =========================================================================

    async def get_dau_trend(self, days: int = 30) -> Dict:
        """
        Get DAU trend.

        Args:
            days: Number of days (1-365)

        Returns:
            Dict with trend data and days
        """
        trend_data = await self._metrics_repo.get_dau_trend(days)
        return {
            "trend": trend_data,
            "days": days
        }
