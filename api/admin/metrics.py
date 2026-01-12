"""
Admin Metrics API - System metrics and analytics.

@module api.admin.metrics
@version 3.28

Changes:
- v3.28: P0/P1/P2 Architecture refactoring
  - MET-CRITICAL-1: Extracted all database access to MetricsRepository
  - MET-HIGH-1: Added query limits to prevent OOM (daily, errors)
  - MET-HIGH-2: Added Pydantic Response Models
  - MET-HIGH-3: Optimized Funnel queries (6 queries → time-filtered queries)
  - MET-HIGH-4: Fixed Funnel period parameter usage (now applies time filter)
  - MET-HIGH-5: Fixed refresh metric_type validation (all/hourly/daily)
  - MET-MEDIUM-1: Added @retry_on_network_error via Repository layer
  - All endpoints now use DDD pattern (API → Repository → Database)
- v3.25: Security improvements
  - MET-MEDIUM-1: Added rate limiting to all endpoints
  - MET-MEDIUM-2: Added date format validation
  - MET-MEDIUM-3: Added months range validation (1-24)
  - MET-MEDIUM-4: Added period enum validation
  - MET-MEDIUM-5: Added hours range validation (1-168)
  - MET-MEDIUM-6: Added days range validation (1-365)
  - MET-MEDIUM-7: Added metric_type enum validation
  - MET-LOW-1: Limited error message exposure

Endpoints:
- GET /metrics/daily - Daily metrics
- GET /metrics/monthly - Monthly metrics
- GET /metrics/retention - User retention
- GET /metrics/funnel - Conversion funnel
- GET /metrics/errors - Error metrics
- GET /metrics/dau-trend - DAU trend
- POST /metrics/refresh - Refresh metrics
"""

import logging
import re
from typing import Optional
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends, Request, Query

from dependencies import require_admin
from core.database import get_async_db_client
from infrastructure.repositories import SupabaseMetricsRepository
from infrastructure.rate_limiter import limiter
from api.admin.metrics_models import (
    DailyMetricsResponse,
    DailyMetricItem,
    MonthlyMetricsResponse,
    MonthlyMetricItem,
    RetentionMetricsResponse,
    FunnelMetricsResponse,
    FunnelStepData,
    ErrorMetricsResponse,
    DAUTrendResponse,
    DAUTrendItem,
    RefreshMetricsResponse,
)
from scheduler import run_aggregation_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["admin-metrics-v2"])


# ==========================================
# Constants (v3.28: Updated for v3.28 fixes)
# ==========================================

# v3.25: MET-MEDIUM-2 - Date format pattern
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?")

# v3.25: MET-MEDIUM-4 - Valid period values
VALID_PERIODS = {"7d", "14d", "30d", "60d", "90d"}

# v3.28: MET-HIGH-5 - Fixed metric types to match scheduler.py
VALID_METRIC_TYPES = {"all", "hourly", "daily"}

# v3.28: MET-HIGH-4 - Period to days mapping
PERIOD_TO_DAYS = {
    "7d": 7,
    "14d": 14,
    "30d": 30,
    "60d": 60,
    "90d": 90,
}


# ==========================================
# Validation Functions (v3.25)
# ==========================================

def validate_date_format(date_str: Optional[str], field_name: str) -> None:
    """Validate date format (YYYY-MM-DD or ISO format)."""
    if date_str is not None and not DATE_PATTERN.match(date_str):
        raise HTTPException(400, f"Invalid {field_name} format. Use YYYY-MM-DD or ISO format")


# ==========================================
# Metrics Routes (v3.28: DDD refactored)
# ==========================================

@router.get("/daily", response_model=DailyMetricsResponse)
@limiter.limit("30/minute")
async def get_daily_metrics(
    request: Request,
    start_date: Optional[str] = Query(None, max_length=30),
    end_date: Optional[str] = Query(None, max_length=30),
    admin: dict = Depends(require_admin)
) -> DailyMetricsResponse:
    """
    Get daily metrics for dashboard.

    v3.28: Refactored to use MetricsRepository (MET-CRITICAL-1).
    v3.28: Added Response Model (MET-HIGH-2).
    v3.28: Added query limit via Repository (MET-HIGH-1).
    """
    # v3.25: MET-MEDIUM-2 - Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    if not start_date:
        start_date = (date.today() - timedelta(days=30)).isoformat()
    if not end_date:
        end_date = date.today().isoformat()

    db = await get_async_db_client()
    metrics_repo = SupabaseMetricsRepository(db)

    try:
        metrics_data = await metrics_repo.get_daily_metrics(start_date, end_date)
        metrics = [DailyMetricItem(**item) for item in metrics_data]
        return DailyMetricsResponse(metrics=metrics, start_date=start_date, end_date=end_date)
    except Exception as e:
        # v3.25: MET-LOW-1 - Limit error exposure
        logger.error(f"[Admin] Error fetching daily metrics: {e}")
        return DailyMetricsResponse(metrics=[], start_date=start_date, end_date=end_date)


@router.get("/monthly", response_model=MonthlyMetricsResponse)
@limiter.limit("30/minute")
async def get_monthly_metrics(
    request: Request,
    # v3.25: MET-MEDIUM-3 - Added months range validation
    months: int = Query(6, ge=1, le=24, description="Number of months (1-24)"),
    admin: dict = Depends(require_admin)
) -> MonthlyMetricsResponse:
    """
    Get monthly aggregated metrics.

    v3.28: Refactored to use MetricsRepository (MET-CRITICAL-1).
    v3.28: Added Response Model (MET-HIGH-2).
    """
    db = await get_async_db_client()
    metrics_repo = SupabaseMetricsRepository(db)

    try:
        metrics_data = await metrics_repo.get_monthly_metrics(months)
        metrics = [MonthlyMetricItem(**item) for item in metrics_data]
        return MonthlyMetricsResponse(metrics=metrics, months=months)
    except Exception as e:
        logger.error(f"[Admin] Error fetching monthly metrics: {e}")
        return MonthlyMetricsResponse(metrics=[], months=months)


@router.get("/retention", response_model=RetentionMetricsResponse)
@limiter.limit("30/minute")
async def get_retention_metrics(
    request: Request,
    admin: dict = Depends(require_admin)
) -> RetentionMetricsResponse:
    """
    Get user retention metrics.

    v3.28: Refactored to use MetricsRepository (MET-CRITICAL-1).
    v3.28: Added Response Model (MET-HIGH-2).
    """
    db = await get_async_db_client()
    metrics_repo = SupabaseMetricsRepository(db)

    try:
        data = await metrics_repo.get_retention_metrics()
        if data:
            return RetentionMetricsResponse(**data)
        return RetentionMetricsResponse()
    except Exception as e:
        logger.error(f"[Admin] Error fetching retention metrics: {e}")
        return RetentionMetricsResponse()


@router.get("/funnel", response_model=FunnelMetricsResponse)
@limiter.limit("30/minute")
async def get_funnel_metrics(
    request: Request,
    # v3.25: MET-MEDIUM-4 - Added period enum validation
    period: str = Query("30d", max_length=10),
    admin: dict = Depends(require_admin)
) -> FunnelMetricsResponse:
    """
    Get conversion funnel metrics.

    v3.28: Refactored to use MetricsRepository (MET-CRITICAL-1).
    v3.28: Added Response Model (MET-HIGH-2).
    v3.28: Fixed period parameter usage - now applies time filter (MET-HIGH-4).
    v3.28: Optimized queries with time range filter (MET-HIGH-3).
    """
    # v3.25: MET-MEDIUM-4 - Validate period
    if period not in VALID_PERIODS:
        raise HTTPException(400, f"Invalid period. Must be one of: {', '.join(VALID_PERIODS)}")

    # v3.28: MET-HIGH-4 - Calculate time range based on period
    days = PERIOD_TO_DAYS.get(period, 30)
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # Define funnel steps
    event_types = [
        "page_view",
        "user_created",
        "project_create",
        "ai_generate",
        "download_pdf",
        "payment_success",
    ]

    step_names = [
        "visitors",
        "signups",
        "first_project",
        "first_generation",
        "first_export",
        "payment",
    ]

    db = await get_async_db_client()
    metrics_repo = SupabaseMetricsRepository(db)

    try:
        # v3.28: Get counts with time range filter
        counts = await metrics_repo.get_funnel_counts(event_types, cutoff_date)

        funnel_data = []
        for event_type, step_name in zip(event_types, step_names):
            funnel_data.append(FunnelStepData(
                step=step_name,
                count=counts.get(event_type, 0)
            ))

        return FunnelMetricsResponse(funnel=funnel_data, period=period)
    except Exception as e:
        logger.error(f"[Admin] Error fetching funnel metrics: {e}")
        return FunnelMetricsResponse(funnel=[], period=period)


@router.get("/errors", response_model=ErrorMetricsResponse)
@limiter.limit("30/minute")
async def get_error_metrics(
    request: Request,
    # v3.25: MET-MEDIUM-5 - Added hours range validation
    hours: int = Query(24, ge=1, le=168, description="Time range in hours (1-168)"),
    admin: dict = Depends(require_admin)
) -> ErrorMetricsResponse:
    """
    Get error metrics summary.

    v3.28: Refactored to use MetricsRepository (MET-CRITICAL-1).
    v3.28: Added Response Model (MET-HIGH-2).
    v3.28: Added query limit via Repository (MET-HIGH-1).
    """
    db = await get_async_db_client()
    metrics_repo = SupabaseMetricsRepository(db)

    try:
        stats = await metrics_repo.get_error_stats(hours)
        return ErrorMetricsResponse(
            total=stats["total"],
            hours=hours,
            by_type=stats["by_type"],
            by_status=stats["by_status"]
        )
    except Exception as e:
        logger.error(f"[Admin] Error fetching error metrics: {e}")
        return ErrorMetricsResponse(total=0, hours=hours, by_type={}, by_status={})


@router.get("/dau-trend", response_model=DAUTrendResponse)
@limiter.limit("30/minute")
async def get_dau_trend(
    request: Request,
    # v3.25: MET-MEDIUM-6 - Added days range validation
    days: int = Query(30, ge=1, le=365, description="Number of days (1-365)"),
    admin: dict = Depends(require_admin)
) -> DAUTrendResponse:
    """
    Get DAU trend.

    v3.28: Refactored to use MetricsRepository (MET-CRITICAL-1).
    v3.28: Added Response Model (MET-HIGH-2).
    """
    db = await get_async_db_client()
    metrics_repo = SupabaseMetricsRepository(db)

    try:
        trend_data = await metrics_repo.get_dau_trend(days)
        trend = [DAUTrendItem(**item) for item in trend_data]
        return DAUTrendResponse(trend=trend, days=days)
    except Exception as e:
        logger.error(f"[Admin] Error fetching DAU trend: {e}")
        return DAUTrendResponse(trend=[], days=days)


@router.post("/refresh", response_model=RefreshMetricsResponse)
@limiter.limit("5/minute")
async def refresh_metrics(
    request: Request,
    # v3.28: MET-HIGH-5 - Fixed metric_type validation to match scheduler.py
    metric_type: str = Query("all", max_length=50),
    admin: dict = Depends(require_admin)
) -> RefreshMetricsResponse:
    """
    Manually refresh metrics aggregation.

    v3.28: Fixed metric_type validation (MET-HIGH-5).
    v3.28: Added Response Model (MET-MEDIUM-4).
    """
    # v3.28: MET-HIGH-5 - Validate metric_type (updated to match scheduler.py)
    if metric_type not in VALID_METRIC_TYPES:
        raise HTTPException(400, f"Invalid metric_type. Must be one of: {', '.join(VALID_METRIC_TYPES)}")

    try:
        result = run_aggregation_now(metric_type)
        return RefreshMetricsResponse(status="refreshed", type=metric_type, result=result)
    except Exception as e:
        logger.error(f"[Admin] Error refreshing metrics: {e}")
        raise HTTPException(500, "Failed to refresh metrics")
