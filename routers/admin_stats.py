"""
Admin Stats Router - Dashboard and analytics endpoints for admins

@module routers.admin_stats
@version 3.24

Endpoints:
- GET /api/admin/stats/dashboard - Dashboard KPIs
- GET /api/admin/stats/user-growth - User growth stats
- GET /api/admin/stats/revenue - Revenue stats
- GET /api/admin/stats/projects - Project stats
- GET /api/admin/stats/credits - Credit usage stats
- GET /api/admin/stats/exports - Export operation stats
- GET /api/admin/stats/assets - Asset usage ranking
- GET /api/admin/stats/tier-distribution - User tier distribution
- GET /api/admin/stats/conversion-funnel - Conversion funnel
- GET /api/admin/stats/tier-activity - Per-tier activity
- GET /api/admin/stats/subscription-events - Subscription events
- GET /api/admin/stats/page-views - Page view stats
- GET /api/admin/stats/project-details - Detailed project stats
- GET /api/admin/stats/returning-users - Returning user stats
- GET /api/admin/stats/tier-trend - Tier trend over time
- GET /api/admin/stats/tier-conversion - Tier conversion stats
- GET /api/admin/stats/performance - Core Web Vitals
- GET /api/admin/stats/user-distribution - User distribution
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends

from services.db_service import (
    supabase,
    admin_get_dashboard_stats,
    admin_get_user_growth_stats,
    admin_get_revenue_stats,
    admin_get_project_stats,
    admin_get_credit_usage_stats,
    admin_get_tier_distribution,
    admin_get_conversion_funnel,
)
from dependencies import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/stats", tags=["admin-stats"])


# ==========================================
# Core Dashboard Stats
# ==========================================

@router.get("/dashboard")
def adm_get_dashboard_stats(
    period: str = "month",
    admin: dict = Depends(require_admin)
):
    """Fetch dashboard KPIs."""
    return admin_get_dashboard_stats(period)


@router.get("/user-growth")
def adm_get_user_growth_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "day",
    admin: dict = Depends(require_admin)
):
    """Fetch user growth stats."""
    return admin_get_user_growth_stats(start_date, end_date, group_by)


@router.get("/revenue")
def adm_get_revenue_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "day",
    admin: dict = Depends(require_admin)
):
    """Fetch revenue stats."""
    return admin_get_revenue_stats(start_date, end_date, group_by)


@router.get("/projects")
def adm_get_project_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """Fetch project stats."""
    return admin_get_project_stats(start_date, end_date)


@router.get("/credits")
def adm_get_credit_usage_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """Fetch credit usage stats."""
    return admin_get_credit_usage_stats(start_date, end_date)


@router.get("/tier-distribution")
def adm_get_tier_distribution(admin: dict = Depends(require_admin)):
    """Fetch user tier distribution."""
    return admin_get_tier_distribution()


@router.get("/conversion-funnel")
def adm_get_conversion_funnel(
    period: str = "month",
    admin: dict = Depends(require_admin)
):
    """Fetch conversion funnel stats."""
    return admin_get_conversion_funnel(period)


# ==========================================
# Aggregated Stats (from aggregated_stats table)
# ==========================================

def _get_aggregated_stat(stat_type: str, default: dict):
    """Helper to fetch pre-aggregated stats."""
    try:
        result = supabase.table("aggregated_stats")\
            .select("data")\
            .eq("stat_type", stat_type)\
            .order("date", desc=True)\
            .limit(1).execute()
        
        if result.data:
            return result.data[0].get("data", default)
        return default
    except Exception as e:
        logger.error(f"Failed to get {stat_type}: {e}")
        return default


@router.get("/exports")
def adm_get_export_stats(admin: dict = Depends(require_admin)):
    """Fetch export operation stats (PDF, ZIP, print, preview)."""
    return _get_aggregated_stat(
        "export_stats_30d",
        {"totalPdf": 0, "totalZip": 0, "totalPrint": 0, "totalPreview": 0, "trend": []}
    )


@router.get("/assets")
def adm_get_asset_usage_stats(admin: dict = Depends(require_admin)):
    """Fetch asset usage ranking stats."""
    return _get_aggregated_stat(
        "asset_usage_ranking",
        {"top_assets": [], "by_type": {}, "total_usage": 0, "total_assets_used": 0}
    )


@router.get("/tier-activity")
def adm_get_tier_activity(admin: dict = Depends(require_admin)):
    """Fetch per-tier activity stats."""
    return _get_aggregated_stat("tier_activity", {})


@router.get("/subscription-events")
def adm_get_subscription_events(admin: dict = Depends(require_admin)):
    """Fetch subscription event stats (upgrade/downgrade/cancel/refund)."""
    return _get_aggregated_stat(
        "subscription_events_30d",
        {"totalUpgrades": 0, "totalDowngrades": 0, "totalCancellations": 0, "totalRefunds": 0, "trend": []}
    )


@router.get("/page-views")
def adm_get_page_views(admin: dict = Depends(require_admin)):
    """Fetch page view stats."""
    return _get_aggregated_stat(
        "page_views_7d",
        {"pages": {}, "total_views": 0, "guest_views": 0}
    )


@router.get("/project-details")
def adm_get_project_details(admin: dict = Depends(require_admin)):
    """Fetch detailed project stats (deleted, OCR, page counts)."""
    return _get_aggregated_stat(
        "project_details_30d",
        {"deleted_projects": 0, "ocr_usage": 0, "total_pages_sample": 0, "avg_pages_per_project": 0}
    )


@router.get("/returning-users")
def adm_get_returning_users(admin: dict = Depends(require_admin)):
    """Fetch returning user stats."""
    return _get_aggregated_stat("returning_users", {})


@router.get("/tier-trend")
def adm_get_tier_trend(admin: dict = Depends(require_admin)):
    """Fetch tier trend (user counts by tier over time)."""
    return _get_aggregated_stat("tier_trend_30d", {"trend": []})


@router.get("/tier-conversion")
def adm_get_tier_conversion(admin: dict = Depends(require_admin)):
    """Fetch tier conversion stats."""
    return _get_aggregated_stat("tier_conversion_30d", {"conversions": []})


@router.get("/performance")
def adm_get_performance_metrics(admin: dict = Depends(require_admin)):
    """Fetch page performance (Core Web Vitals) stats."""
    return _get_aggregated_stat(
        "performance_metrics_7d",
        {"metrics": {}, "by_page": {}, "total_samples": 0}
    )


@router.get("/user-distribution")
def adm_get_user_distribution(admin: dict = Depends(require_admin)):
    """Fetch user distribution stats (country, browser, OS, device)."""
    return _get_aggregated_stat(
        "user_distribution_7d",
        {
            "country": [],
            "browser": [],
            "os": [],
            "device_type": [],
            "language": [],
            "timezone": [],
            "total_sessions": 0
        }
    )
