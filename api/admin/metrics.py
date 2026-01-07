"""
Admin Metrics API - System metrics and analytics.

@module api.admin.metrics
@version 2.0.0

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
from typing import Optional
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends

from dependencies import require_admin
from core.database import get_supabase_client

logger = logging.getLogger(__name__)
supabase = get_supabase_client()

router = APIRouter(prefix="/metrics", tags=["admin-metrics-v2"])


# ==========================================
# Metrics Routes
# ==========================================

@router.get("/daily")
async def get_daily_metrics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """Get daily metrics for dashboard."""
    if not start_date:
        start_date = (date.today() - timedelta(days=30)).isoformat()
    if not end_date:
        end_date = date.today().isoformat()

    try:
        result = supabase.table("daily_metrics").select("*").gte("date", start_date).lte("date", end_date).order("date").execute()
        return {"metrics": result.data or [], "start_date": start_date, "end_date": end_date}
    except Exception as e:
        return {"metrics": [], "error": str(e)}


@router.get("/monthly")
async def get_monthly_metrics(
    months: int = 6,
    admin: dict = Depends(require_admin)
):
    """Get monthly aggregated metrics."""
    try:
        result = supabase.table("monthly_metrics").select("*").order("month", desc=True).limit(months).execute()
        return {"metrics": result.data or [], "months": months}
    except Exception as e:
        return {"metrics": [], "error": str(e)}


@router.get("/retention")
async def get_retention_metrics(admin: dict = Depends(require_admin)):
    """Get user retention metrics."""
    try:
        result = supabase.table("aggregated_stats").select("data").eq("stat_type", "user_retention_30d").order("date", desc=True).limit(1).execute()
        if result.data:
            return result.data[0].get("data", {})
        return {}
    except Exception as e:
        return {"error": str(e)}


@router.get("/funnel")
async def get_funnel_metrics(
    period: str = "30d",
    admin: dict = Depends(require_admin)
):
    """Get conversion funnel metrics."""
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
        return {"funnel": [], "error": str(e)}


@router.get("/errors")
async def get_error_metrics(
    hours: int = 24,
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
        return {"total": 0, "error": str(e)}


@router.get("/dau-trend")
async def get_dau_trend(
    days: int = 30,
    admin: dict = Depends(require_admin)
):
    """Get DAU trend."""
    try:
        result = supabase.table("daily_metrics").select("date, dau").order("date", desc=True).limit(days).execute()
        return {"trend": result.data or [], "days": days}
    except Exception as e:
        return {"trend": [], "error": str(e)}


@router.post("/refresh")
async def refresh_metrics(
    metric_type: str = "all",
    admin: dict = Depends(require_admin)
):
    """Manually refresh metrics aggregation."""
    from scheduler import run_aggregation_now

    try:
        result = run_aggregation_now(metric_type)
        return {"status": "refreshed", "type": metric_type, "result": result}
    except Exception as e:
        raise HTTPException(500, str(e))
