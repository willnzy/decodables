"""
Admin Metrics API - System metrics and analytics.

@module api.admin.metrics
@version 3.29 (Container-based DI)

Changes in v3.29:
- MET-ARCH-1: Migrated to Container-based dependency injection
- MET-ARCH-2: Created AdminMetricsService for business logic
- MET-ARCH-3: Removed direct repository imports from API layer
- Architecture: API → Container → Service → Repository (Strict DIP)

Changes in v3.28:
- MET-CRITICAL-1: Extracted all database access to MetricsRepository
- MET-HIGH-1: Added query limits to prevent OOM (daily, errors)
- MET-HIGH-2: Added Pydantic Response Models
- MET-HIGH-3: Optimized Funnel queries (6 queries → time-filtered queries)
- MET-HIGH-4: Fixed Funnel period parameter usage (now applies time filter)
- MET-HIGH-5: Fixed refresh metric_type validation (all/hourly/daily)
- MET-MEDIUM-1: Added @retry_on_network_error via Repository layer

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

from fastapi import APIRouter, HTTPException, Depends, Request, Query

from dependencies import require_admin
from infrastructure.rate_limiter import limiter

# v3.29: Container-based DI
# WHY: API layer should not know about concrete repository implementations
from container import get_container

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
# Dependency Injection (v3.29: Container-based)
# ==========================================

async def get_admin_metrics_service():
    """
    Get AdminMetricsService from Container.

    WHY Container-based DI?
    1. Decouples API layer from infrastructure implementations
    2. Enables easy testing with mock services
    3. Centralizes dependency management
    4. Supports future provider switches
    """
    container = get_container()
    return await container.get_admin_metrics_service()


# ==========================================
# Constants
# ==========================================

# Date format pattern
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?")

# Valid period values
VALID_PERIODS = {"7d", "14d", "30d", "60d", "90d"}

# Valid metric types for refresh
VALID_METRIC_TYPES = {"all", "hourly", "daily"}


# ==========================================
# Validation Functions
# ==========================================

def validate_date_format(date_str: Optional[str], field_name: str) -> None:
    """Validate date format (YYYY-MM-DD or ISO format)."""
    if date_str is not None and not DATE_PATTERN.match(date_str):
        raise HTTPException(400, f"Invalid {field_name} format. Use YYYY-MM-DD or ISO format")


# ==========================================
# Metrics Routes
# ==========================================

@router.get("/daily", response_model=DailyMetricsResponse)
@limiter.limit("30/minute")
async def get_daily_metrics(
    request: Request,
    start_date: Optional[str] = Query(None, max_length=30),
    end_date: Optional[str] = Query(None, max_length=30),
    admin: dict = Depends(require_admin),
    service=Depends(get_admin_metrics_service),
) -> DailyMetricsResponse:
    """
    Get daily metrics for dashboard.

    v3.29: Refactored to use AdminMetricsService via Container.
    """
    # Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    try:
        result = await service.get_daily_metrics(start_date, end_date)
        metrics = [DailyMetricItem(**item) for item in result["metrics"]]
        return DailyMetricsResponse(
            metrics=metrics,
            start_date=result["start_date"],
            end_date=result["end_date"]
        )
    except Exception as e:
        logger.error(f"[Admin] Error fetching daily metrics: {e}")
        return DailyMetricsResponse(
            metrics=[],
            start_date=start_date or "",
            end_date=end_date or ""
        )


@router.get("/monthly", response_model=MonthlyMetricsResponse)
@limiter.limit("30/minute")
async def get_monthly_metrics(
    request: Request,
    months: int = Query(6, ge=1, le=24, description="Number of months (1-24)"),
    admin: dict = Depends(require_admin),
    service=Depends(get_admin_metrics_service),
) -> MonthlyMetricsResponse:
    """
    Get monthly aggregated metrics.

    v3.29: Refactored to use AdminMetricsService via Container.
    """
    try:
        result = await service.get_monthly_metrics(months)
        metrics = [MonthlyMetricItem(**item) for item in result["metrics"]]
        return MonthlyMetricsResponse(metrics=metrics, months=months)
    except Exception as e:
        logger.error(f"[Admin] Error fetching monthly metrics: {e}")
        return MonthlyMetricsResponse(metrics=[], months=months)


@router.get("/retention", response_model=RetentionMetricsResponse)
@limiter.limit("30/minute")
async def get_retention_metrics(
    request: Request,
    admin: dict = Depends(require_admin),
    service=Depends(get_admin_metrics_service),
) -> RetentionMetricsResponse:
    """
    Get user retention metrics.

    v3.29: Refactored to use AdminMetricsService via Container.
    """
    try:
        data = await service.get_retention_metrics()
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
    period: str = Query("30d", max_length=10),
    admin: dict = Depends(require_admin),
    service=Depends(get_admin_metrics_service),
) -> FunnelMetricsResponse:
    """
    Get conversion funnel metrics.

    v3.29: Refactored to use AdminMetricsService via Container.
    """
    # Validate period
    if period not in VALID_PERIODS:
        raise HTTPException(400, f"Invalid period. Must be one of: {', '.join(VALID_PERIODS)}")

    try:
        result = await service.get_funnel_metrics(period)
        funnel_data = [FunnelStepData(**item) for item in result["funnel"]]
        return FunnelMetricsResponse(funnel=funnel_data, period=period)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"[Admin] Error fetching funnel metrics: {e}")
        return FunnelMetricsResponse(funnel=[], period=period)


@router.get("/errors", response_model=ErrorMetricsResponse)
@limiter.limit("30/minute")
async def get_error_metrics(
    request: Request,
    hours: int = Query(24, ge=1, le=168, description="Time range in hours (1-168)"),
    admin: dict = Depends(require_admin),
    service=Depends(get_admin_metrics_service),
) -> ErrorMetricsResponse:
    """
    Get error metrics summary.

    v3.29: Refactored to use AdminMetricsService via Container.
    """
    try:
        result = await service.get_error_metrics(hours)
        return ErrorMetricsResponse(
            total=result["total"],
            hours=hours,
            by_type=result["by_type"],
            by_status=result["by_status"]
        )
    except Exception as e:
        logger.error(f"[Admin] Error fetching error metrics: {e}")
        return ErrorMetricsResponse(total=0, hours=hours, by_type={}, by_status={})


@router.get("/dau-trend", response_model=DAUTrendResponse)
@limiter.limit("30/minute")
async def get_dau_trend(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="Number of days (1-365)"),
    admin: dict = Depends(require_admin),
    service=Depends(get_admin_metrics_service),
) -> DAUTrendResponse:
    """
    Get DAU trend.

    v3.29: Refactored to use AdminMetricsService via Container.
    """
    try:
        result = await service.get_dau_trend(days)
        trend = [DAUTrendItem(**item) for item in result["trend"]]
        return DAUTrendResponse(trend=trend, days=days)
    except Exception as e:
        logger.error(f"[Admin] Error fetching DAU trend: {e}")
        return DAUTrendResponse(trend=[], days=days)


@router.post("/refresh", response_model=RefreshMetricsResponse)
@limiter.limit("5/minute")
async def refresh_metrics(
    request: Request,
    metric_type: str = Query("all", max_length=50),
    admin: dict = Depends(require_admin),
) -> RefreshMetricsResponse:
    """
    Manually refresh metrics aggregation.

    Note: This endpoint directly calls scheduler, not via service,
    as it's a system operation rather than data retrieval.
    """
    # Validate metric_type
    if metric_type not in VALID_METRIC_TYPES:
        raise HTTPException(400, f"Invalid metric_type. Must be one of: {', '.join(VALID_METRIC_TYPES)}")

    try:
        result = run_aggregation_now(metric_type)
        return RefreshMetricsResponse(status="refreshed", type=metric_type, result=result)
    except Exception as e:
        logger.error(f"[Admin] Error refreshing metrics: {e}")
        raise HTTPException(500, "Failed to refresh metrics")
