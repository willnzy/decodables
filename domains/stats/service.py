"""
Stats Service - Business logic for statistics and analytics.

@module domains.stats.service
@version 3.29 (DDD Compliant)

Changes in v3.29:
- Complete DDD Migration from api/admin/stats.py (STAT-CRITICAL-1)
- All business logic moved to Service layer
- API layer only handles HTTP concerns
- Unified repository access pattern

Architecture:
- API → Service → Repository
- Service layer orchestrates Repository calls
- Centralized logging and error handling
"""

import logging
from typing import Optional, Dict, List, Any

from core.database import get_database_client
from core.database.retry import retry_on_network_error_async
from infrastructure.repositories import SupabaseAdminStatsRepository

logger = logging.getLogger(__name__)


def _get_repos():
    """
    Get repository instances.

    v3.29: DDD Migration helper.
    Returns stats repository used by stats service.
    """
    # TODO: db_client should be passed as parameter (AsyncClient)
    stats_repo = SupabaseAdminStatsRepository(db_client)
    return stats_repo


# ==========================================
# Core Statistics Functions (7)
# ==========================================

async def get_dashboard_stats(period: str = "month") -> Dict[str, Any]:
    """
    Get dashboard statistics.

    v3.29: DDD Migration - Uses Repository.

    Args:
        period: Time period (day/week/month/year)

    Returns:
        Dict with total_users, new_users, total_projects, paying_users
    """
    try:
        stats_repo = _get_repos()
        stats = await stats_repo.admin_get_dashboard_stats(period)
        return stats
    except Exception as e:
        logger.error(f"[Stats] Failed to get dashboard stats: {e}")
        return {"total_users": 0, "new_users": 0, "total_projects": 0, "paying_users": 0}


async def get_user_growth_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "day"
) -> List[Dict[str, Any]]:
    """
    Get user growth statistics.

    v3.29: DDD Migration - Uses Repository.

    Args:
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
        group_by: Group by period (day/week/month)

    Returns:
        List of growth stats by date
    """
    try:
        stats_repo = _get_repos()
        stats = await stats_repo.admin_get_user_growth_stats(start_date, end_date, group_by)
        return stats
    except Exception as e:
        logger.error(f"[Stats] Failed to get user growth stats: {e}")
        return []


async def get_revenue_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "day"
) -> List[Dict[str, Any]]:
    """
    Get revenue statistics.

    v3.29: DDD Migration - Uses Repository.

    Args:
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
        group_by: Group by period (day/week/month)

    Returns:
        List of revenue stats by date
    """
    try:
        stats_repo = _get_repos()
        stats = await stats_repo.admin_get_revenue_stats(start_date, end_date, group_by)
        return stats
    except Exception as e:
        logger.error(f"[Stats] Failed to get revenue stats: {e}")
        return []


async def get_project_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get project statistics.

    v3.29: DDD Migration - Uses Repository.

    Args:
        start_date: Start date (ISO format)
        end_date: End date (ISO format)

    Returns:
        Dict with total and new_in_period counts
    """
    try:
        stats_repo = _get_repos()
        stats = await stats_repo.admin_get_project_stats(start_date, end_date)
        return stats
    except Exception as e:
        logger.error(f"[Stats] Failed to get project stats: {e}")
        return {"total": 0, "new_in_period": 0}


async def get_credit_usage_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get credit usage statistics.

    v3.29: DDD Migration - Uses Repository.

    Args:
        start_date: Start date (ISO format)
        end_date: End date (ISO format)

    Returns:
        Dict with total_used and by_type breakdown
    """
    try:
        stats_repo = _get_repos()
        stats = await stats_repo.admin_get_credit_usage_stats(start_date, end_date)
        return stats
    except Exception as e:
        logger.error(f"[Stats] Failed to get credit usage stats: {e}")
        return {"total_used": 0, "by_type": {}}


async def get_tier_distribution() -> Dict[str, Any]:
    """
    Get user tier distribution.

    v3.29: DDD Migration - Uses Repository.

    Returns:
        Dict with free, starter, pro counts
    """
    try:
        stats_repo = _get_repos()
        distribution = await stats_repo.admin_get_tier_distribution()
        return distribution
    except Exception as e:
        logger.error(f"[Stats] Failed to get tier distribution: {e}")
        return {"t1": 0, "t2": 0, "t3": 0}


async def get_conversion_funnel(period: str = "month") -> Dict[str, Any]:
    """
    Get conversion funnel statistics.

    v3.29: DDD Migration - Uses Repository.

    Args:
        period: Time period (day/week/month/year)

    Returns:
        Dict with signups, created_project, converted counts
    """
    try:
        stats_repo = _get_repos()
        funnel = await stats_repo.admin_get_conversion_funnel(period)
        return funnel
    except Exception as e:
        logger.error(f"[Stats] Failed to get conversion funnel: {e}")
        return {"signups": 0, "created_project": 0, "converted": 0}


# ==========================================
# Aggregated Statistics Functions (11)
# ==========================================

async def get_aggregated_stat(stat_type: str, default: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get aggregated statistic from aggregated_stats table.

    v3.29: DDD Migration - Moved from helper function to Service.
    v3.29: Added defensive logging for unexpected multiple results (STAT-HIGH-1 fix).

    Args:
        stat_type: Type of statistic to fetch
        default: Default value if not found

    Returns:
        Aggregated stat data or default

    OOM Protection: .limit(1) ensures single row fetch.
    """
    try:
        @retry_on_network_error_async()
        async def _fetch():
            result = get_supabase_client().table("aggregated_stats") \
                .select("data") \
                .eq("stat_type", stat_type) \
                .order("date", desc=True) \
                .limit(1).execute()  # OOM Protection + Business Logic

            if result.data:
                if len(result.data) > 1:
                    logger.warning(f"[Stats] Unexpected multiple results for stat_type={stat_type}, using latest")
                return result.data[0].get("data", default)
            return default

        return await _fetch()
    except Exception as e:
        logger.error(f"[Stats] Failed to get aggregated stat {stat_type}: {e}")
        return default


async def get_export_stats() -> Dict[str, Any]:
    """Get export statistics (30 days)."""
    return await get_aggregated_stat(
        "export_stats_30d",
        {"totalPdf": 0, "totalZip": 0, "totalPrint": 0, "totalPreview": 0, "trend": []}
    )


async def get_asset_usage_stats() -> Dict[str, Any]:
    """Get asset usage ranking."""
    return await get_aggregated_stat(
        "asset_usage_ranking",
        {"top_assets": [], "by_type": {}, "total_usage": 0, "total_assets_used": 0}
    )


async def get_tier_activity_stats() -> Dict[str, Any]:
    """Get tier activity statistics."""
    return await get_aggregated_stat("tier_activity", {})


async def get_subscription_events_stats() -> Dict[str, Any]:
    """Get subscription events (30 days)."""
    return await get_aggregated_stat(
        "subscription_events_30d",
        {"totalUpgrades": 0, "totalDowngrades": 0, "totalCancellations": 0, "totalRefunds": 0, "trend": []}
    )


async def get_page_views_stats() -> Dict[str, Any]:
    """Get page views (7 days)."""
    return await get_aggregated_stat(
        "page_views_7d",
        {"pages": {}, "total_views": 0, "guest_views": 0}
    )


async def get_project_details_stats() -> Dict[str, Any]:
    """Get project details (30 days)."""
    return await get_aggregated_stat(
        "project_details_30d",
        {"deleted_projects": 0, "ocr_usage": 0, "total_pages_sample": 0, "avg_pages_per_project": 0}
    )


async def get_returning_users_stats() -> Dict[str, Any]:
    """Get returning users statistics."""
    return await get_aggregated_stat("returning_users", {})


async def get_tier_trend_stats() -> Dict[str, Any]:
    """Get tier trend (30 days)."""
    return await get_aggregated_stat("tier_trend_30d", {"trend": []})


async def get_tier_conversion_stats() -> Dict[str, Any]:
    """Get tier conversion (30 days)."""
    return await get_aggregated_stat("tier_conversion_30d", {"conversions": []})


async def get_performance_metrics_stats() -> Dict[str, Any]:
    """Get performance metrics (7 days)."""
    return await get_aggregated_stat(
        "performance_metrics_7d",
        {"metrics": {}, "by_page": {}, "total_samples": 0}
    )


async def get_user_distribution_stats() -> Dict[str, Any]:
    """Get user distribution (7 days)."""
    return await get_aggregated_stat(
        "user_distribution_7d",
        {"country": [], "browser": [], "os": [], "device_type": [], "language": [], "timezone": [], "total_sessions": 0}
    )
