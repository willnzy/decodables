"""
Admin Events Router - Events and aggregation endpoints for admins

@module api.admin.events
@version 3.25

Changes:
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
- GET /api/admin/events - Get user events
- GET /api/admin/events/stats - Get event statistics
- GET /api/admin/aggregated/{stat_type} - Get aggregated stats
- GET /api/admin/aggregated/{stat_type}/range - Get stats over range
- POST /api/admin/aggregation/run - Run aggregation task
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

@router.get("/events")
@limiter.limit("30/minute")
async def adm_get_user_events(
    request: Request,
    event_type: Optional[str] = Query(None, max_length=100, description="Filter by event type"),
    user_id: Optional[str] = Query(None, max_length=50, description="Filter by user ID"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD or ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD or ISO format)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Page size (1-1000)"),
    admin: dict = Depends(require_admin)
):
    """Fetch user events (with optional filters)."""
    # v3.25: EVT-MEDIUM-3 - Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    db_client = get_database_client()
    stats_repo = SupabaseAdminStatsRepository(db_client)
    # Convert offset to page for repository compatibility
    page = (offset // limit) + 1 if limit > 0 else 1
    return await stats_repo.admin_get_user_events(
        event_type=event_type,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        limit=limit
    )


@router.get("/events/stats")
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

    db_client = get_database_client()
    stats_repo = SupabaseAdminStatsRepository(db_client)
    return await stats_repo.admin_get_event_stats(start_date, end_date, group_by)


# ==========================================
# Aggregated Stats Endpoints (v3.25: Added rate limiting and validation)
# ==========================================

@router.get("/aggregated/{stat_type}")
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

    db_client = get_database_client()
    stats_repo = SupabaseAdminStatsRepository(db_client)
    data = await stats_repo.get_aggregated_stats(stat_type, use_cache)

    if data is None:
        return {"data": None, "message": "No cached data available. Run aggregation task first."}

    return {"data": data}


@router.get("/aggregated/{stat_type}/range")
@limiter.limit("30/minute")
async def adm_get_aggregated_stats_range(
    request: Request,
    stat_type: str,
    # v3.25: EVT-MEDIUM-6 - Days range validation
    days: int = Query(30, ge=1, le=365, description="Number of days (1-365)"),
    admin: dict = Depends(require_admin)
):
    """Fetch aggregated stats over a specific number of days."""
    # v3.25: EVT-MEDIUM-5 - Validate stat_type parameter
    if stat_type not in VALID_STAT_TYPES:
        raise HTTPException(400, f"Invalid stat_type. Must be one of: {', '.join(VALID_STAT_TYPES)}")

    db_client = get_database_client()
    stats_repo = SupabaseAdminStatsRepository(db_client)
    return await stats_repo.get_aggregated_stats_range(stat_type, days)


@router.post("/aggregation/run")
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
        result = run_aggregation_now(task_type)
        return result
    except Exception as e:
        logger.error(f"Failed to run aggregation: {e}")
        raise HTTPException(500, "Failed to run aggregation task")
