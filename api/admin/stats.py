"""
Admin Stats API - Dashboard and analytics endpoints for admins.

@module api.admin.stats
@version 3.30 (P2-001 Fix: Typed Response Models)

Changes:
- v3.30: P2-001 Fix - Migrate to Pydantic response models
  - All endpoints now return typed Pydantic models
  - API layer converts Service dict results to typed entities
  - Type safety throughout the stack
  - Consistent response structure with timestamps

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
from typing import Optional, List, Dict, Any

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
# v3.30: Import Pydantic models (P2-001 Fix)
from domains.stats.models import (
    DashboardStats,
    UserGrowthDataPoint,
    RevenueDataPoint,
    ProjectStats,
    CreditUsageStats,
    TierDistributionItem,
    ConversionFunnelStep,
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

@router.get("/dashboard", response_model=DashboardStats)
@limiter.limit("30/minute")
async def get_dashboard_stats_endpoint(
    request: Request,
    period: str = Query("month", max_length=10),
    admin: dict = Depends(require_admin),
) -> DashboardStats:
    """Fetch dashboard KPIs."""
    # v3.25: STAT-MEDIUM-3 - Validate period enum
    if period not in VALID_DASHBOARD_PERIODS:
        raise HTTPException(400, f"Invalid period. Must be one of: {', '.join(VALID_DASHBOARD_PERIODS)}")

    try:
        result = await get_dashboard_stats(period)
        # v3.30: Convert dict to Pydantic model (P2-001 Fix)
        return DashboardStats(**result)
    except Exception as e:
        logger.error(f"Failed to fetch dashboard stats: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch dashboard statistics")


@router.get("/user-growth", response_model=List[UserGrowthDataPoint])
@limiter.limit("30/minute")
async def get_user_growth_stats_endpoint(
    request: Request,
    start_date: Optional[str] = Query(None, max_length=30),
    end_date: Optional[str] = Query(None, max_length=30),
    group_by: str = Query("day", max_length=10),
    admin: dict = Depends(require_admin),
) -> List[UserGrowthDataPoint]:
    """Fetch user growth stats."""
    # v3.25: STAT-MEDIUM-2 - Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    # v3.25: STAT-MEDIUM-3 - Validate group_by enum
    if group_by not in VALID_GROUP_BY:
        raise HTTPException(400, f"Invalid group_by. Must be one of: {', '.join(VALID_GROUP_BY)}")

    try:
        result = await get_user_growth_stats(start_date, end_date, group_by)
        # v3.30: Convert list of dicts to Pydantic models (P2-001 Fix)
        return [UserGrowthDataPoint(**item) for item in result]
    except Exception as e:
        logger.error(f"Failed to fetch user growth stats: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch user growth statistics")


@router.get("/revenue", response_model=List[RevenueDataPoint])
@limiter.limit("30/minute")
async def get_revenue_stats_endpoint(
    request: Request,
    start_date: Optional[str] = Query(None, max_length=30),
    end_date: Optional[str] = Query(None, max_length=30),
    group_by: str = Query("day", max_length=10),
    admin: dict = Depends(require_admin),
) -> List[RevenueDataPoint]:
    """Fetch revenue stats."""
    # v3.25: STAT-MEDIUM-2 - Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    # v3.25: STAT-MEDIUM-3 - Validate group_by enum
    if group_by not in VALID_GROUP_BY:
        raise HTTPException(400, f"Invalid group_by. Must be one of: {', '.join(VALID_GROUP_BY)}")

    try:
        result = await get_revenue_stats(start_date, end_date, group_by)
        # v3.30: Convert list of dicts to Pydantic models (P2-001 Fix)
        return [RevenueDataPoint(**item) for item in result]
    except Exception as e:
        logger.error(f"Failed to fetch revenue stats: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch revenue statistics")


@router.get("/projects", response_model=ProjectStats)
@limiter.limit("30/minute")
async def get_project_stats_endpoint(
    request: Request,
    start_date: Optional[str] = Query(None, max_length=30),
    end_date: Optional[str] = Query(None, max_length=30),
    admin: dict = Depends(require_admin),
) -> ProjectStats:
    """Fetch project stats."""
    # v3.25: STAT-MEDIUM-2 - Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    try:
        result = await get_project_stats(start_date, end_date)
        # v3.30: Convert dict to Pydantic model (P2-001 Fix)
        return ProjectStats(**result)
    except Exception as e:
        logger.error(f"Failed to fetch project stats: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch project statistics")


@router.get("/credits", response_model=CreditUsageStats)
@limiter.limit("30/minute")
async def get_credit_usage_stats_endpoint(
    request: Request,
    start_date: Optional[str] = Query(None, max_length=30),
    end_date: Optional[str] = Query(None, max_length=30),
    admin: dict = Depends(require_admin),
) -> CreditUsageStats:
    """Fetch credit usage stats."""
    # v3.25: STAT-MEDIUM-2 - Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    try:
        result = await get_credit_usage_stats(start_date, end_date)
        # v3.30: Convert dict to Pydantic model (P2-001 Fix)
        return CreditUsageStats(**result)
    except Exception as e:
        logger.error(f"Failed to fetch credit usage stats: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch credit usage statistics")


@router.get("/tier-distribution", response_model=List[TierDistributionItem])
@limiter.limit("30/minute")
async def get_tier_distribution_endpoint(
    request: Request,
    admin: dict = Depends(require_admin),
) -> List[TierDistributionItem]:
    """Fetch user tier distribution."""
    try:
        result = await get_tier_distribution()
        # v3.30: Convert dict to list of Pydantic models (P2-001 Fix)
        # Result format: {"t1": 100, "t2": 50, "t3": 20}
        total = sum(result.values())
        return [
            TierDistributionItem(
                tier=tier,
                count=count,
                percentage=round((count / total * 100) if total > 0 else 0, 2)
            )
            for tier, count in result.items()
        ]
    except Exception as e:
        logger.error(f"Failed to fetch tier distribution: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch tier distribution")


@router.get("/conversion-funnel", response_model=List[ConversionFunnelStep])
@limiter.limit("30/minute")
async def get_conversion_funnel_endpoint(
    request: Request,
    period: str = Query("month", max_length=10),
    admin: dict = Depends(require_admin),
) -> List[ConversionFunnelStep]:
    """Fetch conversion funnel stats."""
    # v3.25: STAT-MEDIUM-3 - Validate period enum
    if period not in VALID_DASHBOARD_PERIODS:
        raise HTTPException(400, f"Invalid period. Must be one of: {', '.join(VALID_DASHBOARD_PERIODS)}")

    try:
        result = await get_conversion_funnel(period)
        # v3.30: Convert dict to list of Pydantic models (P2-001 Fix)
        # Result format: {"signups": 100, "created_project": 50, "converted": 10}
        steps_data = [
            {"step": "signups", "count": result.get("signups", 0), "conversion_rate": None},
            {
                "step": "created_project",
                "count": result.get("created_project", 0),
                "conversion_rate": round((result.get("created_project", 0) / result.get("signups", 1) * 100), 2) if result.get("signups", 0) > 0 else 0
            },
            {
                "step": "converted",
                "count": result.get("converted", 0),
                "conversion_rate": round((result.get("converted", 0) / result.get("created_project", 1) * 100), 2) if result.get("created_project", 0) > 0 else 0
            }
        ]
        return [ConversionFunnelStep(**step) for step in steps_data]
    except Exception as e:
        logger.error(f"Failed to fetch conversion funnel: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch conversion funnel")


# ==========================================
# Aggregated Stats (v3.25: Added rate limiting)
# ==========================================

@router.get("/exports")
@limiter.limit("30/minute")
async def get_export_stats_endpoint(request: Request, admin: dict = Depends(require_admin)) -> Dict[str, Any]:
    """Fetch export operation stats (PDF, ZIP, print, preview)."""
    # v3.30: Fixed - call Service layer function (P2-001 Fix)
    return await get_export_stats()


@router.get("/assets")
@limiter.limit("30/minute")
async def get_asset_usage_stats_endpoint(request: Request, admin: dict = Depends(require_admin)) -> Dict[str, Any]:
    """Fetch asset usage ranking stats."""
    # v3.30: Fixed - call Service layer function (P2-001 Fix)
    return await get_asset_usage_stats()


@router.get("/tier-activity")
@limiter.limit("30/minute")
async def get_tier_activity_endpoint(request: Request, admin: dict = Depends(require_admin)) -> Dict[str, Any]:
    """Fetch per-tier activity stats."""
    return await get_tier_activity_stats()


@router.get("/subscription-events")
@limiter.limit("30/minute")
async def get_subscription_events_endpoint(request: Request, admin: dict = Depends(require_admin)) -> Dict[str, Any]:
    """Fetch subscription event stats."""
    # v3.30: Fixed - call Service layer function (P2-001 Fix)
    return await get_subscription_events_stats()


@router.get("/page-views")
@limiter.limit("30/minute")
async def get_page_views_endpoint(request: Request, admin: dict = Depends(require_admin)) -> Dict[str, Any]:
    """Fetch page view stats."""
    # v3.30: Fixed - call Service layer function (P2-001 Fix)
    return await get_page_views_stats()


@router.get("/project-details")
@limiter.limit("30/minute")
async def get_project_details_endpoint(request: Request, admin: dict = Depends(require_admin)) -> Dict[str, Any]:
    """Fetch detailed project stats."""
    # v3.30: Fixed - call Service layer function (P2-001 Fix)
    return await get_project_details_stats()


@router.get("/returning-users")
@limiter.limit("30/minute")
async def get_returning_users_endpoint(request: Request, admin: dict = Depends(require_admin)) -> Dict[str, Any]:
    """Fetch returning user stats."""
    return await get_returning_users_stats()


@router.get("/tier-trend")
@limiter.limit("30/minute")
async def get_tier_trend_endpoint(request: Request, admin: dict = Depends(require_admin)) -> Dict[str, Any]:
    """Fetch tier trend over time."""
    return await get_tier_trend_stats()


@router.get("/tier-conversion")
@limiter.limit("30/minute")
async def get_tier_conversion_endpoint(request: Request, admin: dict = Depends(require_admin)) -> Dict[str, Any]:
    """Fetch tier conversion stats."""
    return await get_tier_conversion_stats()


@router.get("/performance")
@limiter.limit("30/minute")
async def get_performance_metrics_endpoint(request: Request, admin: dict = Depends(require_admin)) -> Dict[str, Any]:
    """Fetch page performance (Core Web Vitals) stats."""
    # v3.30: Fixed - call Service layer function (P2-001 Fix)
    return await get_performance_metrics_stats()


@router.get("/user-distribution")
@limiter.limit("30/minute")
async def get_user_distribution_endpoint(request: Request, admin: dict = Depends(require_admin)) -> Dict[str, Any]:
    """Fetch user distribution stats."""
    # v3.30: Fixed - call Service layer function (P2-001 Fix)
    return await get_user_distribution_stats()
