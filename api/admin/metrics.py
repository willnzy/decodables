"""
Admin Metrics API - System metrics and analytics.

@module api.admin.metrics
@version 3.25

Changes:
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
from core.database import get_supabase_client
from infrastructure.rate_limiter import limiter

logger = logging.getLogger(__name__)
supabase = get_supabase_client()

router = APIRouter(prefix="/metrics", tags=["admin-metrics-v2"])


# ==========================================
# Constants (v3.25)
# ==========================================

# v3.25: MET-MEDIUM-2 - Date format pattern
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?")

# v3.25: MET-MEDIUM-4 - Valid period values
VALID_PERIODS = {"7d", "14d", "30d", "60d", "90d"}

# v3.25: MET-MEDIUM-7 - Valid metric types
VALID_METRIC_TYPES = {"all", "daily", "monthly", "retention", "funnel"}


# ==========================================
# Validation Functions (v3.25)
# ==========================================

def validate_date_format(date_str: Optional[str], field_name: str) -> None:
    """Validate date format (YYYY-MM-DD or ISO format)."""
    if date_str is not None and not DATE_PATTERN.match(date_str):
        raise HTTPException(400, f"Invalid {field_name} format. Use YYYY-MM-DD or ISO format")


# ==========================================
# Metrics Routes (v3.25: Added rate limiting and validation)
# ==========================================

@router.get("/daily")
@limiter.limit("30/minute")
async def get_daily_metrics(
    request: Request,
    start_date: Optional[str] = Query(None, max_length=30),
    end_date: Optional[str] = Query(None, max_length=30),
    admin: dict = Depends(require_admin)
):
    """Get daily metrics for dashboard."""
    # v3.25: MET-MEDIUM-2 - Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    if not start_date:
        start_date = (date.today() - timedelta(days=30)).isoformat()
    if not end_date:
        end_date = date.today().isoformat()

    try:
        result = supabase.table("daily_metrics").select("*").gte("date", start_date).lte("date", end_date).order("date").execute()
        return {"metrics": result.data or [], "start_date": start_date, "end_date": end_date}
    except Exception as e:
        # v3.25: MET-LOW-1 - Limit error exposure
        logger.error(f"[Admin] Error fetching daily metrics: {e}")
        return {"metrics": [], "error": "Failed to fetch daily metrics"}


@router.get("/monthly")
@limiter.limit("30/minute")
async def get_monthly_metrics(
    request: Request,
    # v3.25: MET-MEDIUM-3 - Added months range validation
    months: int = Query(6, ge=1, le=24, description="Number of months (1-24)"),
    admin: dict = Depends(require_admin)
):
    """Get monthly aggregated metrics."""
    try:
        result = supabase.table("monthly_metrics").select("*").order("month", desc=True).limit(months).execute()
        return {"metrics": result.data or [], "months": months}
    except Exception as e:
        logger.error(f"[Admin] Error fetching monthly metrics: {e}")
        return {"metrics": [], "error": "Failed to fetch monthly metrics"}


@router.get("/retention")
@limiter.limit("30/minute")
async def get_retention_metrics(
    request: Request,
    admin: dict = Depends(require_admin)
):
    """Get user retention metrics."""
    try:
        result = supabase.table("aggregated_stats").select("data").eq("stat_type", "user_retention_30d").order("date", desc=True).limit(1).execute()
        if result.data:
            return result.data[0].get("data", {})
        return {}
    except Exception as e:
        logger.error(f"[Admin] Error fetching retention metrics: {e}")
        return {"error": "Failed to fetch retention metrics"}


@router.get("/funnel")
@limiter.limit("30/minute")
async def get_funnel_metrics(
    request: Request,
    # v3.25: MET-MEDIUM-4 - Added period enum validation
    period: str = Query("30d", max_length=10),
    admin: dict = Depends(require_admin)
):
    """Get conversion funnel metrics."""
    # v3.25: MET-MEDIUM-4 - Validate period
    if period not in VALID_PERIODS:
        raise HTTPException(400, f"Invalid period. Must be one of: {', '.join(VALID_PERIODS)}")

    try:
        # Define funnel steps
        steps = [
            {"name": "visitors", "query": "page_view"},
            {"name": "signups", "query": "user_created"},
            {"name": "first_project", "query": "project_create"},
            {"name": "first_generation", "query": "ai_generate"},
            {"name": "first_export", "query": "download_pdf"},
            {"name": "payment", "query": "payment_success"},
        ]

        funnel_data = []
        for step in steps:
            count_result = supabase.table("user_events").select("id", count="exact").eq("event_type", step["query"]).execute()
            funnel_data.append({
                "step": step["name"],
                "count": count_result.count or 0
            })

        return {"funnel": funnel_data, "period": period}
    except Exception as e:
        logger.error(f"[Admin] Error fetching funnel metrics: {e}")
        return {"funnel": [], "error": "Failed to fetch funnel metrics"}


@router.get("/errors")
@limiter.limit("30/minute")
async def get_error_metrics(
    request: Request,
    # v3.25: MET-MEDIUM-5 - Added hours range validation
    hours: int = Query(24, ge=1, le=168, description="Time range in hours (1-168)"),
    admin: dict = Depends(require_admin)
):
    """Get error metrics summary."""
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        result = supabase.table("error_logs").select("error_type, status_code").gte("created_at", cutoff).execute()

        errors = result.data or []
        by_type = {}
        by_status = {}

        for err in errors:
            t = err.get("error_type", "UNKNOWN")
            by_type[t] = by_type.get(t, 0) + 1

            s = err.get("status_code", 0)
            by_status[s] = by_status.get(s, 0) + 1

        return {
            "total": len(errors),
            "hours": hours,
            "by_type": by_type,
            "by_status": by_status
        }
    except Exception as e:
        logger.error(f"[Admin] Error fetching error metrics: {e}")
        return {"total": 0, "error": "Failed to fetch error metrics"}


@router.get("/dau-trend")
@limiter.limit("30/minute")
async def get_dau_trend(
    request: Request,
    # v3.25: MET-MEDIUM-6 - Added days range validation
    days: int = Query(30, ge=1, le=365, description="Number of days (1-365)"),
    admin: dict = Depends(require_admin)
):
    """Get DAU trend."""
    try:
        result = supabase.table("daily_metrics").select("date, dau").order("date", desc=True).limit(days).execute()
        return {"trend": result.data or [], "days": days}
    except Exception as e:
        logger.error(f"[Admin] Error fetching DAU trend: {e}")
        return {"trend": [], "error": "Failed to fetch DAU trend"}


@router.post("/refresh")
@limiter.limit("5/minute")
async def refresh_metrics(
    request: Request,
    # v3.25: MET-MEDIUM-7 - Added metric_type enum validation
    metric_type: str = Query("all", max_length=50),
    admin: dict = Depends(require_admin)
):
    """Manually refresh metrics aggregation."""
    # v3.25: MET-MEDIUM-7 - Validate metric_type
    if metric_type not in VALID_METRIC_TYPES:
        raise HTTPException(400, f"Invalid metric_type. Must be one of: {', '.join(VALID_METRIC_TYPES)}")

    from scheduler import run_aggregation_now

    try:
        result = run_aggregation_now(metric_type)
        return {"status": "refreshed", "type": metric_type, "result": result}
    except Exception as e:
        logger.error(f"[Admin] Error refreshing metrics: {e}")
        raise HTTPException(500, "Failed to refresh metrics")
