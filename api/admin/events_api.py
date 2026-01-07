"""
Admin Events API - Events and aggregation endpoints for admins.

@module api.admin.events_api
@version 2.0.0

Endpoints:
- GET /events - Get user events
- GET /events/stats - Get event statistics
- GET /aggregated/{stat_type} - Get aggregated stats
- GET /aggregated/{stat_type}/range - Get stats over range
- POST /aggregation/run - Run aggregation task
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends

from dependencies import require_admin
from services.db_service import (
    admin_get_user_events,
    admin_get_event_stats,
    get_aggregated_stats,
    get_aggregated_stats_range,
)
from scheduler import run_aggregation_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["admin-events"])


# ==========================================
# Events Endpoints
# ==========================================

@router.get("")
def get_user_events(
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


@router.get("/stats")
def get_event_stats(
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
def get_aggregated(
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
def get_aggregated_range(
    stat_type: str,
    days: int = 30,
    admin: dict = Depends(require_admin)
):
    """Fetch aggregated stats over a specific number of days."""
    return get_aggregated_stats_range(stat_type, days)


@router.post("/aggregation/run")
def run_aggregation(
    task_type: str = "all",
    admin: dict = Depends(require_admin)
):
    """Manually trigger aggregation task (task_type: all | hourly | daily)."""
    return run_aggregation_now(task_type)
