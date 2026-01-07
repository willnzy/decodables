"""
Admin Stats API - Dashboard and analytics endpoints for admins.

@module api.admin.stats
@version 2.0.0

Endpoints:
- GET /stats/dashboard - Dashboard KPIs
- GET /stats/user-growth - User growth stats
- GET /stats/revenue - Revenue stats
- GET /stats/projects - Project stats
- GET /stats/credits - Credit usage stats
- GET /stats/tier-distribution - User tier distribution
- GET /stats/conversion-funnel - Conversion funnel
- GET /stats/exports - Export operation stats
- GET /stats/assets - Asset usage ranking
- GET /stats/tier-activity - Per-tier activity
- GET /stats/subscription-events - Subscription events
- GET /stats/page-views - Page view stats
- GET /stats/project-details - Detailed project stats
- GET /stats/returning-users - Returning user stats
- GET /stats/tier-trend - Tier trend over time
- GET /stats/tier-conversion - Tier conversion stats
- GET /stats/performance - Core Web Vitals
- GET /stats/user-distribution - User distribution
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query

from dependencies import require_admin
from core.database import get_database_client, get_supabase_client
from infrastructure.repositories import SupabaseAdminStatsRepositoryExtended

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stats", tags=["admin-stats-v2"])


# ==========================================
# Helper Functions
# ==========================================

async def _get_aggregated_stat(stat_type: str, default: dict):
    """Fetch pre-aggregated stats from database."""
    try:
        result = get_supabase_client().table("aggregated_stats") \
            .select("data") \
            .eq("stat_type", stat_type) \
            .order("date", desc=True) \
            .limit(1).execute()

        if result.data:
            return result.data[0].get("data", default)
        return default
    except Exception as e:
        logger.error(f"Failed to get {stat_type}: {e}")
        return default


# ==========================================
# Core Dashboard Stats
# ==========================================

@router.get("/dashboard")
async def get_dashboard_stats(
    period: str = Query("month", pattern="^(day|week|month|year)$"),
    admin: dict = Depends(require_admin),
):
    """Fetch dashboard KPIs."""
    db_client = get_database_client()
    stats_repo = SupabaseAdminStatsRepositoryExtended(db_client)
    return await stats_repo.admin_get_dashboard_stats(period)


@router.get("/user-growth")
async def get_user_growth_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = Query("day", pattern="^(day|week|month)$"),
    admin: dict = Depends(require_admin),
):
    """Fetch user growth stats."""
    db_client = get_database_client()
    stats_repo = SupabaseAdminStatsRepositoryExtended(db_client)
    return await stats_repo.admin_get_user_growth_stats(start_date, end_date, group_by)


@router.get("/revenue")
async def get_revenue_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = Query("day", pattern="^(day|week|month)$"),
    admin: dict = Depends(require_admin),
):
    """Fetch revenue stats."""
    db_client = get_database_client()
    stats_repo = SupabaseAdminStatsRepositoryExtended(db_client)
    return await stats_repo.admin_get_revenue_stats(start_date, end_date, group_by)


@router.get("/projects")
async def get_project_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin: dict = Depends(require_admin),
):
    """Fetch project stats."""
    db_client = get_database_client()
    stats_repo = SupabaseAdminStatsRepositoryExtended(db_client)
    return await stats_repo.admin_get_project_stats(start_date, end_date)


@router.get("/credits")
async def get_credit_usage_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin: dict = Depends(require_admin),
):
    """Fetch credit usage stats."""
    db_client = get_database_client()
    stats_repo = SupabaseAdminStatsRepositoryExtended(db_client)
    return await stats_repo.admin_get_credit_usage_stats(start_date, end_date)


@router.get("/tier-distribution")
async def get_tier_distribution(
    admin: dict = Depends(require_admin),
):
    """Fetch user tier distribution."""
    db_client = get_database_client()
    stats_repo = SupabaseAdminStatsRepositoryExtended(db_client)
    return await stats_repo.admin_get_tier_distribution()


@router.get("/conversion-funnel")
async def get_conversion_funnel(
    period: str = Query("month", pattern="^(day|week|month|year)$"),
    admin: dict = Depends(require_admin),
):
    """Fetch conversion funnel stats."""
    db_client = get_database_client()
    stats_repo = SupabaseAdminStatsRepositoryExtended(db_client)
    return await stats_repo.admin_get_conversion_funnel(period)


# ==========================================
# Aggregated Stats
# ==========================================

@router.get("/exports")
async def get_export_stats(admin: dict = Depends(require_admin)):
    """Fetch export operation stats (PDF, ZIP, print, preview)."""
    return await _get_aggregated_stat(
        "export_stats_30d",
        {"totalPdf": 0, "totalZip": 0, "totalPrint": 0, "totalPreview": 0, "trend": []},
    )


@router.get("/assets")
async def get_asset_usage_stats(admin: dict = Depends(require_admin)):
    """Fetch asset usage ranking stats."""
    return await _get_aggregated_stat(
        "asset_usage_ranking",
        {"top_assets": [], "by_type": {}, "total_usage": 0, "total_assets_used": 0},
    )


@router.get("/tier-activity")
async def get_tier_activity(admin: dict = Depends(require_admin)):
    """Fetch per-tier activity stats."""
    return await _get_aggregated_stat("tier_activity", {})


@router.get("/subscription-events")
async def get_subscription_events(admin: dict = Depends(require_admin)):
    """Fetch subscription event stats."""
    return await _get_aggregated_stat(
        "subscription_events_30d",
        {"totalUpgrades": 0, "totalDowngrades": 0, "totalCancellations": 0, "totalRefunds": 0, "trend": []},
    )


@router.get("/page-views")
async def get_page_views(admin: dict = Depends(require_admin)):
    """Fetch page view stats."""
    return await _get_aggregated_stat(
        "page_views_7d",
        {"pages": {}, "total_views": 0, "guest_views": 0},
    )


@router.get("/project-details")
async def get_project_details(admin: dict = Depends(require_admin)):
    """Fetch detailed project stats."""
    return await _get_aggregated_stat(
        "project_details_30d",
        {"deleted_projects": 0, "ocr_usage": 0, "total_pages_sample": 0, "avg_pages_per_project": 0},
    )


@router.get("/returning-users")
async def get_returning_users(admin: dict = Depends(require_admin)):
    """Fetch returning user stats."""
    return await _get_aggregated_stat("returning_users", {})


@router.get("/tier-trend")
async def get_tier_trend(admin: dict = Depends(require_admin)):
    """Fetch tier trend over time."""
    return await _get_aggregated_stat("tier_trend_30d", {"trend": []})


@router.get("/tier-conversion")
async def get_tier_conversion(admin: dict = Depends(require_admin)):
    """Fetch tier conversion stats."""
    return await _get_aggregated_stat("tier_conversion_30d", {"conversions": []})


@router.get("/performance")
async def get_performance_metrics(admin: dict = Depends(require_admin)):
    """Fetch page performance (Core Web Vitals) stats."""
    return await _get_aggregated_stat(
        "performance_metrics_7d",
        {"metrics": {}, "by_page": {}, "total_samples": 0},
    )


@router.get("/user-distribution")
async def get_user_distribution(admin: dict = Depends(require_admin)):
    """Fetch user distribution stats."""
    return await _get_aggregated_stat(
        "user_distribution_7d",
        {
            "country": [],
            "browser": [],
            "os": [],
            "device_type": [],
            "language": [],
            "timezone": [],
            "total_sessions": 0,
        },
    )
