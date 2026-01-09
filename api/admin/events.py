"""
Admin Events Router - Events and aggregation endpoints for admins

@module api.admin.events
@version 3.26

Changes:
- v3.26: Complete architecture refactor (2026-01-09)
  - EVT-CRITICAL-1: Fixed start_date/end_date parameter support
  - EVT-CRITICAL-2: Fixed end_date and group_by in stats
  - EVT-HIGH-1: Unified offset pagination (removed page conversion)
  - EVT-HIGH-2: Added .limit(100000) to prevent OOM
  - EVT-HIGH-3: Added Pydantic Response Models
  - EVT-HIGH-4: Repository returns Dict with pagination info
  - EVT-MEDIUM-1: Added unified error handling
  - EVT-MEDIUM-2: Implemented full group_by support (4 types)
  - EVT-MEDIUM-3: Reduced limit max from 1000 to 100
  - EVT-LOW-1/2: Added audit logging for all operations

- v3.25: Security improvements
  - EVT-MEDIUM-1: Added rate limiting to all endpoints
  - EVT-MEDIUM-2: Added event_type validation
  - EVT-MEDIUM-3: Added date format validation
  - EVT-MEDIUM-4: Added group_by enum validation
  - EVT-MEDIUM-5: Added stat_type enum validation
  - EVT-MEDIUM-6: Added days range validation (1-365)
  - EVT-MEDIUM-7: Added task_type enum validation
  - EVT-LOW-1: Migrated page to offset pagination

Endpoints:
- GET /api/admin/events/events - Get user events
- GET /api/admin/events/events/stats - Get event statistics
- GET /api/admin/events/aggregated/{stat_type} - Get aggregated stats
- GET /api/admin/events/aggregated/{stat_type}/range - Get stats over range
- POST /api/admin/events/aggregation/run - Run aggregation task
"""

import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query

from core.database import get_database_client
from infrastructure.repositories import SupabaseAdminStatsRepository
from infrastructure.rate_limiter import limiter
from scheduler import run_aggregation_now
from dependencies import require_admin
from .events_models import (
    UserEventsResponse,
    EventStatsResponse,
    AggregatedStatsResponse,
    AggregatedStatsRangeResponse,
    AggregationTriggerResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["admin-events-v2"])


# ==========================================
# Constants (v3.25)
# ==========================================

# v3.25: EVT-MEDIUM-3 - Date format validation pattern
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?")

# v3.25: EVT-MEDIUM-4 - Valid group_by values
VALID_GROUP_BY = {"event_type", "user_id", "date", "hour"}

# v3.25: EVT-MEDIUM-5 - Valid stat_types
VALID_STAT_TYPES = {
    "daily_users", "daily_revenue", "daily_projects", "credit_usage_30d",
    "tier_distribution", "conversion_funnel_30d", "event_stats_7d",
    "monthly_metrics", "retention_metrics"
}

# v3.25: EVT-MEDIUM-7 - Valid task_types
VALID_TASK_TYPES = {"all", "hourly", "daily"}


def validate_date_format(date_str: Optional[str], field_name: str) -> None:
    """v3.25: EVT-MEDIUM-3 - Validate date format (YYYY-MM-DD or ISO)."""
    if date_str is not None and not DATE_PATTERN.match(date_str):
        raise HTTPException(400, f"Invalid {field_name} format. Use YYYY-MM-DD or ISO format")


# ==========================================
# Events Endpoints (v3.25: Added rate limiting and validation)
# ==========================================

@router.get("/events", response_model=UserEventsResponse)
@limiter.limit("30/minute")
async def adm_get_user_events(
    request: Request,
    event_type: Optional[str] = Query(None, max_length=100, description="Filter by event type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD or ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD or ISO format)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    # v3.26: EVT-MEDIUM-3 - Reduced limit max from 1000 to 100
    limit: int = Query(100, ge=1, le=100, description="Page size (1-100)"),
    admin: dict = Depends(require_admin)
):
    """Fetch user events (with optional filters)."""
    # v3.25: EVT-MEDIUM-3 - Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    try:
        db_client = get_database_client()
        stats_repo = SupabaseAdminStatsRepository(db_client)

        # v3.26: EVT-LOW-1 - Add audit logging
        logger.info(f"[Admin {admin.get('id')}] Queried user events (offset={offset}, limit={limit})")

        # v3.26: EVT-HIGH-1 - Direct offset pagination (no conversion)
        result = await stats_repo.admin_get_user_events(
            user_id=user_id,
            event_type=event_type,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            limit=limit
        )
        return result
    except Exception as e:
        # v3.26: EVT-MEDIUM-1 - Unified error handling
        logger.error(f"[Admin] Get user events failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve user events")


@router.get("/events/stats", response_model=EventStatsResponse)
@limiter.limit("30/minute")
async def adm_get_event_stats(
    request: Request,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD or ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD or ISO format)"),
    group_by: str = Query("event_type", description="Group by field: event_type, user_id, date, hour"),
    admin: dict = Depends(require_admin)
):
    """Fetch event statistics (grouped by event_type by default)."""
    # v3.25: EVT-MEDIUM-3 - Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    # v3.25: EVT-MEDIUM-4 - Validate group_by parameter
    if group_by not in VALID_GROUP_BY:
        raise HTTPException(400, f"Invalid group_by. Must be one of: {', '.join(VALID_GROUP_BY)}")

    try:
        db_client = get_database_client()
        stats_repo = SupabaseAdminStatsRepository(db_client)

        # v3.26: EVT-LOW-1 - Add audit logging
        logger.info(f"[Admin {admin.get('id')}] Queried event stats (group_by={group_by})")

        stats = await stats_repo.admin_get_event_stats(start_date, end_date, group_by)
        return {
            "stats": stats,
            "group_by": group_by,
            "start_date": start_date,
            "end_date": end_date
        }
    except Exception as e:
        # v3.26: EVT-MEDIUM-1 - Unified error handling
        logger.error(f"[Admin] Get event stats failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve event statistics")


# ==========================================
# Aggregated Stats Endpoints (v3.25: Added rate limiting and validation)
# ==========================================

@router.get("/aggregated/{stat_type}", response_model=AggregatedStatsResponse)
@limiter.limit("30/minute")
async def adm_get_aggregated_stats(
    request: Request,
    stat_type: str,
    use_cache: bool = Query(True, description="Use cached data"),
    admin: dict = Depends(require_admin)
):
    """
    Fetch aggregated stats for the given stat_type.
    Supported types: daily_users, daily_revenue, daily_projects, credit_usage_30d,
    tier_distribution, conversion_funnel_30d, event_stats_7d, etc.
    """
    # v3.25: EVT-MEDIUM-5 - Validate stat_type parameter
    if stat_type not in VALID_STAT_TYPES:
        raise HTTPException(400, f"Invalid stat_type. Must be one of: {', '.join(VALID_STAT_TYPES)}")

    try:
        db_client = get_database_client()
        stats_repo = SupabaseAdminStatsRepository(db_client)

        # v3.26: EVT-LOW-1 - Add audit logging
        logger.info(f"[Admin {admin.get('id')}] Queried aggregated stats (stat_type={stat_type})")

        data = await stats_repo.get_aggregated_stats(stat_type, use_cache)

        if data is None:
            return {"data": None, "message": "No cached data available. Run aggregation task first."}

        return {"data": data}
    except Exception as e:
        # v3.26: EVT-MEDIUM-1 - Unified error handling
        logger.error(f"[Admin] Get aggregated stats failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve aggregated statistics")


@router.get("/aggregated/{stat_type}/range", response_model=AggregatedStatsRangeResponse)
@limiter.limit("30/minute")
async def adm_get_aggregated_stats_range(
    request: Request,
    stat_type: str,
    days: int = Query(30, ge=1, le=365, description="Number of days (1-365)"),
    admin: dict = Depends(require_admin)
):
    """Fetch aggregated stats over a specific number of days."""
    # v3.25: EVT-MEDIUM-5 - Validate stat_type parameter
    if stat_type not in VALID_STAT_TYPES:
        raise HTTPException(400, f"Invalid stat_type. Must be one of: {', '.join(VALID_STAT_TYPES)}")

    try:
        db_client = get_database_client()
        stats_repo = SupabaseAdminStatsRepository(db_client)

        # v3.26: EVT-LOW-1 - Add audit logging
        logger.info(f"[Admin {admin.get('id')}] Queried aggregated stats range (stat_type={stat_type}, days={days})")

        stats = await stats_repo.get_aggregated_stats_range(stat_type, days)
        return {
            "stats": stats,
            "stat_type": stat_type,
            "days": days
        }
    except Exception as e:
        # v3.26: EVT-MEDIUM-1 - Unified error handling
        logger.error(f"[Admin] Get aggregated stats range failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve aggregated statistics range")


@router.post("/aggregation/run", response_model=AggregationTriggerResponse)
@limiter.limit("5/minute")
async def adm_run_aggregation(
    request: Request,
    task_type: str = Query("all", description="Task type: all, hourly, daily"),
    admin: dict = Depends(require_admin)
):
    """Manually trigger aggregation task (task_type: all | hourly | daily)."""
    # v3.25: EVT-MEDIUM-7 - Validate task_type parameter
    if task_type not in VALID_TASK_TYPES:
        raise HTTPException(400, f"Invalid task_type. Must be one of: {', '.join(VALID_TASK_TYPES)}")

    try:
        # v3.26: EVT-LOW-2 - Add audit logging
        logger.info(f"[Admin {admin.get('id')}] Manually triggered aggregation: {task_type}")

        result = run_aggregation_now(task_type)

        # Ensure result conforms to response model
        if isinstance(result, dict):
            return {
                "status": result.get("status", "completed"),
                "task_type": task_type,
                "message": result.get("message"),
                "details": result
            }
        else:
            return {
                "status": "completed",
                "task_type": task_type,
                "details": {"result": str(result)}
            }
    except Exception as e:
        # v3.26: EVT-MEDIUM-1 - Unified error handling
        logger.error(f"[Admin] Run aggregation failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to run aggregation task")
