"""
Admin Events Router - Events and aggregation endpoints for admins

@module api.admin.events
@version 3.24

Endpoints:
- GET /api/admin/events - Get user events
- GET /api/admin/events/stats - Get event statistics
- GET /api/admin/aggregated/{stat_type} - Get aggregated stats
- GET /api/admin/aggregated/{stat_type}/range - Get stats over range
- POST /api/admin/aggregation/run - Run aggregation task
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends

from infrastructure.db_compat import (
    admin_get_user_events,
    admin_get_event_stats,
    get_aggregated_stats,
    get_aggregated_stats_range,
)
from scheduler import run_aggregation_now
from dependencies import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["admin-events-v2"])


# ==========================================
# Events Endpoints
# ==========================================

@router.get("/events")
def adm_get_user_events(
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    limit: int = 100,
    admin: dict = Depends(require_admin)
):
    """Fetch user events (with optional filters)."""
    return admin_get_user_events(
        event_type=event_type,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        limit=limit
    )


@router.get("/events/stats")
def adm_get_event_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "event_type",
    admin: dict = Depends(require_admin)
):
    """Fetch event statistics (grouped by event_type by default)."""
    return admin_get_event_stats(start_date, end_date, group_by)


# ==========================================
# Aggregated Stats Endpoints
# ==========================================

@router.get("/aggregated/{stat_type}")
def adm_get_aggregated_stats(
    stat_type: str,
    use_cache: bool = True,
    admin: dict = Depends(require_admin)
):
    """
    Fetch aggregated stats for the given stat_type.
    Supported types: daily_users, daily_revenue, daily_projects, credit_usage_30d,
    tier_distribution, conversion_funnel_30d, event_stats_7d, etc.
    """
    data = get_aggregated_stats(stat_type, use_cache)
    
    if data is None:
        return {"data": None, "message": "No cached data available. Run aggregation task first."}
    
    return {"data": data}


@router.get("/aggregated/{stat_type}/range")
def adm_get_aggregated_stats_range(
    stat_type: str,
    days: int = 30,
    admin: dict = Depends(require_admin)
):
    """Fetch aggregated stats over a specific number of days."""
    return get_aggregated_stats_range(stat_type, days)


@router.post("/aggregation/run")
def adm_run_aggregation(
    task_type: str = "all",
    admin: dict = Depends(require_admin)
):
    """Manually trigger aggregation task (task_type: all | hourly | daily)."""
    return run_aggregation_now(task_type)
