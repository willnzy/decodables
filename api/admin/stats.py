"""
Admin Stats API - Dashboard and analytics endpoints for admins.

@module api.admin.stats
@version 3.31 (Field mapping fix)

Changes:
- v3.31: Fixed field mapping between Repository and Pydantic models
  - user-growth: Map {date, count} to {date, new_users, total_users}
  - credits: Map {total_used, by_type} to {total_credits_purchased, total_credits_consumed, avg_credits_per_user}

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
    # Core Stats Models (1-7)
    DashboardStats,
    UserGrowthDataPoint,
    RevenueDataPoint,
    ProjectStats,
    CreditUsageStats,
    TierDistributionItem,
    ConversionFunnelStep,
    # Aggregated Stats Response Models (8-18) - P3-001 Fix
    ExportStatsResponse,
    AssetUsageResponse,
    TierActivityStatsResponse,
    SubscriptionEventsResponse,
    PageViewsResponse,
    ProjectDetailsResponse,
    ReturningUsersStatsResponse,
    TierTrendResponse,
    TierConversionResponse,
    PerformanceMetricsResponse,
    UserDistributionResponse,
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
        # v3.31: Map repository data to Pydantic models
        # Repository returns: {"date": "2026-01-20", "count": 10}
        # Model needs: {"date": ..., "new_users": ..., "total_users": ...}
        cumulative = 0
        growth_data = []
        for item in result:
            cumulative += item.get("count", 0)
            growth_data.append(UserGrowthDataPoint(
                date=item.get("date", ""),
                new_users=item.get("count", 0),
                total_users=cumulative
            ))
        return growth_data
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
        # v3.31: Map repository data to Pydantic model
        # Repository returns: {"total_used": 100, "by_type": {...}}
        # Model needs: total_credits_purchased, total_credits_consumed, avg_credits_per_user
        total_consumed = result.get("total_used", 0)
        return CreditUsageStats(
            total_credits_purchased=0,  # Not tracked in current schema
            total_credits_consumed=total_consumed,
            avg_credits_per_user=0.0  # Would need user count to calculate
        )
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

@router.get("/exports", response_model=ExportStatsResponse)
@limiter.limit("30/minute")
async def get_export_stats_endpoint(request: Request, admin: dict = Depends(require_admin)) -> ExportStatsResponse:
    """Fetch export operation stats (PDF, ZIP, print, preview)."""
    # v3.30: P3-001 Fix - Add typed response model
    try:
        raw_data = await get_export_stats()
        # Transform raw aggregated data to typed response
        from domains.stats.models import ExportStatsItem
        exports = [
            ExportStatsItem(export_type="pdf", count=raw_data.get("totalPdf", 0), avg_duration_seconds=None),
            ExportStatsItem(export_type="zip", count=raw_data.get("totalZip", 0), avg_duration_seconds=None),
            ExportStatsItem(export_type="print", count=raw_data.get("totalPrint", 0), avg_duration_seconds=None),
            ExportStatsItem(export_type="preview", count=raw_data.get("totalPreview", 0), avg_duration_seconds=None),
        ]
        total_exports = sum([e.count for e in exports])
        return ExportStatsResponse(exports=exports, total_exports=total_exports)
    except Exception as e:
        logger.error(f"Failed to fetch export stats: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch export statistics")


@router.get("/assets", response_model=AssetUsageResponse)
@limiter.limit("30/minute")
async def get_asset_usage_stats_endpoint(request: Request, admin: dict = Depends(require_admin)) -> AssetUsageResponse:
    """Fetch asset usage ranking stats."""
    # v3.30: P3-001 Fix - Add typed response model
    try:
        raw_data = await get_asset_usage_stats()
        # Transform raw aggregated data to typed response
        from domains.stats.models import AssetUsageRanking
        assets = [
            AssetUsageRanking(
                asset_id=item.get("asset_id", ""),
                asset_name=item.get("asset_name"),
                usage_count=item.get("usage_count", 0),
                unique_users=item.get("unique_users", 0)
            )
            for item in raw_data.get("top_assets", [])
        ]
        return AssetUsageResponse(
            assets=assets,
            total_assets=raw_data.get("total_assets_used", len(assets))
        )
    except Exception as e:
        logger.error(f"Failed to fetch asset usage stats: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch asset usage statistics")


@router.get("/tier-activity", response_model=TierActivityStatsResponse)
@limiter.limit("30/minute")
async def get_tier_activity_endpoint(request: Request, admin: dict = Depends(require_admin)) -> TierActivityStatsResponse:
    """Fetch per-tier activity stats."""
    # v3.30: P3-001 Fix - Add typed response model
    try:
        raw_data = await get_tier_activity_stats()
        # Transform raw aggregated data to typed response
        from domains.stats.models import TierActivityStats
        tier_stats = [
            TierActivityStats(
                tier=tier_key,
                active_users=tier_data.get("active_users", 0),
                total_projects=tier_data.get("total_projects", 0),
                avg_projects_per_user=tier_data.get("avg_projects_per_user", 0.0)
            )
            for tier_key, tier_data in raw_data.items()
            if isinstance(tier_data, dict)
        ]
        return TierActivityStatsResponse(tier_stats=tier_stats)
    except Exception as e:
        logger.error(f"Failed to fetch tier activity stats: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch tier activity statistics")


@router.get("/subscription-events", response_model=SubscriptionEventsResponse)
@limiter.limit("30/minute")
async def get_subscription_events_endpoint(request: Request, admin: dict = Depends(require_admin)) -> SubscriptionEventsResponse:
    """Fetch subscription event stats."""
    # v3.30: P3-001 Fix - Add typed response model
    try:
        raw_data = await get_subscription_events_stats()
        # Transform raw aggregated data to typed response
        from domains.stats.models import SubscriptionEventItem
        events = []
        for trend_item in raw_data.get("trend", []):
            if isinstance(trend_item, dict) and "date" in trend_item:
                # Each trend item contains multiple event types
                for event_type in ["upgrades", "downgrades", "cancellations", "refunds"]:
                    if event_type in trend_item:
                        events.append(SubscriptionEventItem(
                            date=trend_item["date"],
                            event_type=event_type,
                            count=trend_item[event_type]
                        ))
        total_events = raw_data.get("totalUpgrades", 0) + raw_data.get("totalDowngrades", 0) + \
                       raw_data.get("totalCancellations", 0) + raw_data.get("totalRefunds", 0)
        return SubscriptionEventsResponse(events=events, total_events=total_events)
    except Exception as e:
        logger.error(f"Failed to fetch subscription events: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch subscription event statistics")


@router.get("/page-views", response_model=PageViewsResponse)
@limiter.limit("30/minute")
async def get_page_views_endpoint(request: Request, admin: dict = Depends(require_admin)) -> PageViewsResponse:
    """Fetch page view stats."""
    # v3.30: P3-001 Fix - Add typed response model
    try:
        raw_data = await get_page_views_stats()
        # Transform raw aggregated data to typed response
        from domains.stats.models import PageViewsDataPoint
        # Convert pages dict to list of data points
        page_views = [
            PageViewsDataPoint(
                date=page_key,
                page_views=page_data.get("views", 0) if isinstance(page_data, dict) else 0,
                unique_visitors=page_data.get("unique", 0) if isinstance(page_data, dict) else 0
            )
            for page_key, page_data in raw_data.get("pages", {}).items()
        ]
        return PageViewsResponse(page_views=page_views)
    except Exception as e:
        logger.error(f"Failed to fetch page views: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch page view statistics")


@router.get("/project-details", response_model=ProjectDetailsResponse)
@limiter.limit("30/minute")
async def get_project_details_endpoint(request: Request, admin: dict = Depends(require_admin)) -> ProjectDetailsResponse:
    """Fetch detailed project stats."""
    # v3.30: P3-001 Fix - Add typed response model
    try:
        raw_data = await get_project_details_stats()
        # Transform raw aggregated data to typed response
        from domains.stats.models import ProjectDetailsDataPoint
        # Since aggregated_stats stores summary data, create a single data point
        projects = [
            ProjectDetailsDataPoint(
                date="aggregated",  # Aggregated stats don't have daily breakdown
                projects_created=raw_data.get("total_pages_sample", 0),
                projects_published=0,  # Not tracked in current schema
                projects_deleted=raw_data.get("deleted_projects", 0)
            )
        ]
        return ProjectDetailsResponse(projects=projects)
    except Exception as e:
        logger.error(f"Failed to fetch project details: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch project detail statistics")


@router.get("/returning-users", response_model=ReturningUsersStatsResponse)
@limiter.limit("30/minute")
async def get_returning_users_endpoint(request: Request, admin: dict = Depends(require_admin)) -> ReturningUsersStatsResponse:
    """Fetch returning user stats."""
    # v3.30: P3-001 Fix - Add typed response model
    try:
        raw_data = await get_returning_users_stats()
        # Transform raw aggregated data to typed response
        from domains.stats.models import ReturningUsersStats
        stats = ReturningUsersStats(
            returning_users_count=raw_data.get("returning_users_count", 0),
            new_users_count=raw_data.get("new_users_count", 0),
            retention_rate=raw_data.get("retention_rate", 0.0)
        )
        return ReturningUsersStatsResponse(stats=stats)
    except Exception as e:
        logger.error(f"Failed to fetch returning users stats: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch returning user statistics")


@router.get("/tier-trend", response_model=TierTrendResponse)
@limiter.limit("30/minute")
async def get_tier_trend_endpoint(request: Request, admin: dict = Depends(require_admin)) -> TierTrendResponse:
    """Fetch tier trend over time."""
    # v3.30: P3-001 Fix - Add typed response model
    try:
        raw_data = await get_tier_trend_stats()
        # Transform raw aggregated data to typed response
        from domains.stats.models import TierTrendDataPoint
        trend = [
            TierTrendDataPoint(
                date=item.get("date", ""),
                t1_count=item.get("t1", 0),
                t2_count=item.get("t2", 0),
                t3_count=item.get("t3", 0)
            )
            for item in raw_data.get("trend", [])
            if isinstance(item, dict)
        ]
        return TierTrendResponse(trend=trend)
    except Exception as e:
        logger.error(f"Failed to fetch tier trend: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch tier trend statistics")


@router.get("/tier-conversion", response_model=TierConversionResponse)
@limiter.limit("30/minute")
async def get_tier_conversion_endpoint(request: Request, admin: dict = Depends(require_admin)) -> TierConversionResponse:
    """Fetch tier conversion stats."""
    # v3.30: P3-001 Fix - Add typed response model
    try:
        raw_data = await get_tier_conversion_stats()
        # Transform raw aggregated data to typed response
        from domains.stats.models import TierConversionMatrix
        conversions = [
            TierConversionMatrix(
                from_tier=item.get("from_tier", ""),
                to_tier=item.get("to_tier", ""),
                conversion_count=item.get("count", 0),
                conversion_rate=item.get("rate", 0.0)
            )
            for item in raw_data.get("conversions", [])
            if isinstance(item, dict)
        ]
        total_conversions = sum(c.conversion_count for c in conversions)
        return TierConversionResponse(conversions=conversions, total_conversions=total_conversions)
    except Exception as e:
        logger.error(f"Failed to fetch tier conversion: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch tier conversion statistics")


@router.get("/performance", response_model=PerformanceMetricsResponse)
@limiter.limit("30/minute")
async def get_performance_metrics_endpoint(request: Request, admin: dict = Depends(require_admin)) -> PerformanceMetricsResponse:
    """Fetch page performance (Core Web Vitals) stats."""
    # v3.30: P3-001 Fix - Add typed response model
    try:
        raw_data = await get_performance_metrics_stats()
        # Transform raw aggregated data to typed response
        from domains.stats.models import PerformanceMetrics
        metrics_dict = raw_data.get("metrics", {})
        metrics = PerformanceMetrics(
            avg_lcp=metrics_dict.get("avg_lcp"),
            avg_fid=metrics_dict.get("avg_fid"),
            avg_cls=metrics_dict.get("avg_cls"),
            avg_ttfb=metrics_dict.get("avg_ttfb")
        )
        return PerformanceMetricsResponse(metrics=metrics)
    except Exception as e:
        logger.error(f"Failed to fetch performance metrics: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch performance metrics")


@router.get("/user-distribution", response_model=UserDistributionResponse)
@limiter.limit("30/minute")
async def get_user_distribution_endpoint(request: Request, admin: dict = Depends(require_admin)) -> UserDistributionResponse:
    """Fetch user distribution stats."""
    # v3.30: P3-001 Fix - Add typed response model
    try:
        raw_data = await get_user_distribution_stats()
        # Transform raw aggregated data to typed response
        from domains.stats.models import UserDistributionItem
        distribution = []
        total_users = raw_data.get("total_sessions", 0)

        # Process each dimension (country, browser, os, device_type, language, timezone)
        for dimension in ["country", "browser", "os", "device_type", "language", "timezone"]:
            dimension_data = raw_data.get(dimension, [])
            if isinstance(dimension_data, list):
                for item in dimension_data:
                    if isinstance(item, dict):
                        user_count = item.get("count", 0)
                        distribution.append(UserDistributionItem(
                            dimension=dimension,
                            value=item.get("value", "unknown"),
                            user_count=user_count,
                            percentage=round((user_count / total_users * 100), 2) if total_users > 0 else 0.0
                        ))

        return UserDistributionResponse(distribution=distribution, total_users=total_users)
    except Exception as e:
        logger.error(f"Failed to fetch user distribution: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to fetch user distribution statistics")
