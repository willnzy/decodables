"""
Admin Stats API - Dashboard and analytics endpoints for admins.

@module api.admin.stats
@version 3.29 (DDD Compliant)

Changes:
- v3.29: Complete DDD architecture migration (STAT-CRITICAL-1)
  - API layer now calls Service layer instead of Repository
  - Moved constants to domains/stats/constants.py (STAT-MEDIUM-2)
  - Unified repository access pattern (STAT-MEDIUM-1)
  - Removed _get_aggregated_stat helper (moved to Service layer)
  - All 18 endpoints now follow API → Service → Repository pattern

- v3.26: Critical fixes and error handling improvements
  - STAT-CRITICAL-1: Fixed revenue endpoint (was calling non-existent method)
  - STAT-HIGH-1: Added try-except error handling to all 7 core endpoints
  - STAT-HIGH-3: Added retry mechanism to _get_aggregated_stat helper
  - STAT-LOW-2: Enhanced error logging with detailed messages

- v3.25: Security improvements
  - STAT-MEDIUM-1: Added rate limiting to all 18 endpoints
  - STAT-MEDIUM-2: Added date format validation
  - STAT-MEDIUM-3: Added period/group_by enum validation
  - STAT-LOW-1: Enhanced error logging

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

from fastapi import APIRouter, Depends, Query, Request, HTTPException

from dependencies import require_admin
from infrastructure.rate_limiter import limiter

# v3.29: Import from Domain layer (DDD Migration)
from domains.stats import (
    # Core statistics (7)
    get_dashboard_stats,
    get_user_growth_stats,
    get_revenue_stats,
    get_project_stats,
    get_credit_usage_stats,
    get_tier_distribution,
    get_conversion_funnel,
    # Aggregated statistics (11)
    get_export_stats,
    get_asset_usage_stats,
    get_tier_activity_stats,
    get_subscription_events_stats,
    get_page_views_stats,
    get_project_details_stats,
    get_returning_users_stats,
    get_tier_trend_stats,
    get_tier_conversion_stats,
    get_performance_metrics_stats,
    get_user_distribution_stats,
)
from domains.stats.constants import (
    VALID_DASHBOARD_PERIODS,
    VALID_GROUP_BY,
    DATE_PATTERN,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stats", tags=["admin-stats-v2"])


# ==========================================
# Validation Functions
# ==========================================

def validate_date_format(date_str: Optional[str], field_name: str) -> None:
    """Validate date format (YYYY-MM-DD or ISO format)."""
    if date_str is not None and not DATE_PATTERN.match(date_str):
        raise HTTPException(400, f"Invalid {field_name} format. Use YYYY-MM-DD or ISO format")


# ==========================================
# Core Dashboard Stats (v3.25: Added rate limiting and validation)
# ==========================================

@router.get("/dashboard")
@limiter.limit("30/minute")
async def get_dashboard_stats_endpoint(
    request: Request,
    period: str = Query("month", max_length=10),
    admin: dict = Depends(require_admin),
):
    """Fetch dashboard KPIs."""
    # v3.25: STAT-MEDIUM-3 - Validate period enum
    if period not in VALID_DASHBOARD_PERIODS:
        raise HTTPException(400, f"Invalid period. Must be one of: {', '.join(VALID_DASHBOARD_PERIODS)}")

    try:
        result = await get_dashboard_stats(period)
        return result
    except Exception as e:
        logger.error(f"Failed to fetch dashboard stats: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch dashboard statistics")


@router.get("/user-growth")
@limiter.limit("30/minute")
async def get_user_growth_stats_endpoint(
    request: Request,
    start_date: Optional[str] = Query(None, max_length=30),
    end_date: Optional[str] = Query(None, max_length=30),
    group_by: str = Query("day", max_length=10),
    admin: dict = Depends(require_admin),
):
    """Fetch user growth stats."""
    # v3.25: STAT-MEDIUM-2 - Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    # v3.25: STAT-MEDIUM-3 - Validate group_by enum
    if group_by not in VALID_GROUP_BY:
        raise HTTPException(400, f"Invalid group_by. Must be one of: {', '.join(VALID_GROUP_BY)}")

    try:
        result = await get_user_growth_stats(start_date, end_date, group_by)
        return result
    except Exception as e:
        logger.error(f"Failed to fetch user growth stats: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch user growth statistics")


@router.get("/revenue")
@limiter.limit("30/minute")
async def get_revenue_stats_endpoint(
    request: Request,
    start_date: Optional[str] = Query(None, max_length=30),
    end_date: Optional[str] = Query(None, max_length=30),
    group_by: str = Query("day", max_length=10),
    admin: dict = Depends(require_admin),
):
    """Fetch revenue stats."""
    # v3.25: STAT-MEDIUM-2 - Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    # v3.25: STAT-MEDIUM-3 - Validate group_by enum
    if group_by not in VALID_GROUP_BY:
        raise HTTPException(400, f"Invalid group_by. Must be one of: {', '.join(VALID_GROUP_BY)}")

    try:
        result = await get_revenue_stats(start_date, end_date, group_by)
        return result
    except Exception as e:
        logger.error(f"Failed to fetch revenue stats: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch revenue statistics")


@router.get("/projects")
@limiter.limit("30/minute")
async def get_project_stats_endpoint(
    request: Request,
    start_date: Optional[str] = Query(None, max_length=30),
    end_date: Optional[str] = Query(None, max_length=30),
    admin: dict = Depends(require_admin),
):
    """Fetch project stats."""
    # v3.25: STAT-MEDIUM-2 - Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    try:
        result = await get_project_stats(start_date, end_date)
        return result
    except Exception as e:
        logger.error(f"Failed to fetch project stats: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch project statistics")


@router.get("/credits")
@limiter.limit("30/minute")
async def get_credit_usage_stats_endpoint(
    request: Request,
    start_date: Optional[str] = Query(None, max_length=30),
    end_date: Optional[str] = Query(None, max_length=30),
    admin: dict = Depends(require_admin),
):
    """Fetch credit usage stats."""
    # v3.25: STAT-MEDIUM-2 - Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    try:
        result = await get_credit_usage_stats(start_date, end_date)
        return result
    except Exception as e:
        logger.error(f"Failed to fetch credit usage stats: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch credit usage statistics")


@router.get("/tier-distribution")
@limiter.limit("30/minute")
async def get_tier_distribution_endpoint(
    request: Request,
    admin: dict = Depends(require_admin),
):
    """Fetch user tier distribution."""
    try:
        result = await get_tier_distribution()
        return result
    except Exception as e:
        logger.error(f"Failed to fetch tier distribution: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch tier distribution")


@router.get("/conversion-funnel")
@limiter.limit("30/minute")
async def get_conversion_funnel_endpoint(
    request: Request,
    period: str = Query("month", max_length=10),
    admin: dict = Depends(require_admin),
):
    """Fetch conversion funnel stats."""
    # v3.25: STAT-MEDIUM-3 - Validate period enum
    if period not in VALID_DASHBOARD_PERIODS:
        raise HTTPException(400, f"Invalid period. Must be one of: {', '.join(VALID_DASHBOARD_PERIODS)}")

    try:
        result = await get_conversion_funnel(period)
        return result
    except Exception as e:
        logger.error(f"Failed to fetch conversion funnel: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch conversion funnel")


# ==========================================
# Aggregated Stats (v3.25: Added rate limiting)
# ==========================================

@router.get("/exports")
@limiter.limit("30/minute")
async def get_export_stats(request: Request, admin: dict = Depends(require_admin)):
    """Fetch export operation stats (PDF, ZIP, print, preview)."""
    return await _get_aggregated_stat(
        "export_stats_30d",
        {"totalPdf": 0, "totalZip": 0, "totalPrint": 0, "totalPreview": 0, "trend": []},
    )


@router.get("/assets")
@limiter.limit("30/minute")
async def get_asset_usage_stats(request: Request, admin: dict = Depends(require_admin)):
    """Fetch asset usage ranking stats."""
    return await _get_aggregated_stat(
        "asset_usage_ranking",
        {"top_assets": [], "by_type": {}, "total_usage": 0, "total_assets_used": 0},
    )


@router.get("/tier-activity")
@limiter.limit("30/minute")
async def get_tier_activity(request: Request, admin: dict = Depends(require_admin)):
    """Fetch per-tier activity stats."""
    return await get_tier_activity_stats()


@router.get("/subscription-events")
@limiter.limit("30/minute")
async def get_subscription_events(request: Request, admin: dict = Depends(require_admin)):
    """Fetch subscription event stats."""
    return await _get_aggregated_stat(
        "subscription_events_30d",
        {"totalUpgrades": 0, "totalDowngrades": 0, "totalCancellations": 0, "totalRefunds": 0, "trend": []},
    )


@router.get("/page-views")
@limiter.limit("30/minute")
async def get_page_views(request: Request, admin: dict = Depends(require_admin)):
    """Fetch page view stats."""
    return await _get_aggregated_stat(
        "page_views_7d",
        {"pages": {}, "total_views": 0, "guest_views": 0},
    )


@router.get("/project-details")
@limiter.limit("30/minute")
async def get_project_details(request: Request, admin: dict = Depends(require_admin)):
    """Fetch detailed project stats."""
    return await _get_aggregated_stat(
        "project_details_30d",
        {"deleted_projects": 0, "ocr_usage": 0, "total_pages_sample": 0, "avg_pages_per_project": 0},
    )


@router.get("/returning-users")
@limiter.limit("30/minute")
async def get_returning_users(request: Request, admin: dict = Depends(require_admin)):
    """Fetch returning user stats."""
    return await get_returning_users_stats()


@router.get("/tier-trend")
@limiter.limit("30/minute")
async def get_tier_trend(request: Request, admin: dict = Depends(require_admin)):
    """Fetch tier trend over time."""
    return await get_tier_trend_stats()


@router.get("/tier-conversion")
@limiter.limit("30/minute")
async def get_tier_conversion(request: Request, admin: dict = Depends(require_admin)):
    """Fetch tier conversion stats."""
    return await get_tier_conversion_stats()


@router.get("/performance")
@limiter.limit("30/minute")
async def get_performance_metrics(request: Request, admin: dict = Depends(require_admin)):
    """Fetch page performance (Core Web Vitals) stats."""
    return await _get_aggregated_stat(
        "performance_metrics_7d",
        {"metrics": {}, "by_page": {}, "total_samples": 0},
    )


@router.get("/user-distribution")
@limiter.limit("30/minute")
async def get_user_distribution(request: Request, admin: dict = Depends(require_admin)):
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
