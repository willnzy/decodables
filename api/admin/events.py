"""
Admin Events Router - Events and aggregation endpoints for admins

@module api.admin.events
@version 3.27

Changes:
- v3.27: DDD Architecture Refactor (2026-01-09)
  - EVT-CRITICAL-1: Created DDD three-layer architecture
    * Created domains/events/ (Entity, Repository Interface, Domain Service, Constants)
    * Created application/services/events_service.py (Use Case orchestration)
    * Created infrastructure/repositories/events_repository.py (Supabase implementation)
  - EVT-CRITICAL-2: API now calls Service instead of Repository directly
  - EVT-HIGH-1: Migrated constants to Domain layer
  - EVT-HIGH-4: Added @retry_on_network_error to get_user_events
  - EVT-MEDIUM-1: Improved error handling (distinguish 400 vs 500)
  - EVT-MEDIUM-2: Migrated validation logic to Domain Service

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
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query

from core.database import get_database_client
from infrastructure.repositories.events_repository import SupabaseEventsRepository
from application.services.events_service import EventsService
from infrastructure.rate_limiter import limiter
from scheduler import run_aggregation_now
from dependencies import require_admin
from domains.events import (
    VALID_GROUP_BY,
    VALID_STAT_TYPES,
    VALID_TASK_TYPES,
    MAX_LIMIT,
    MAX_RANGE_DAYS,
)
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
# Events Endpoints
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
    limit: int = Query(50, ge=1, le=MAX_LIMIT, description=f"Page size (1-{MAX_LIMIT})"),
    admin: dict = Depends(require_admin)
):
    """Fetch user events (with optional filters)."""
    try:
        logger.info(
            f"[Admin {admin.get('id')}] Getting user events "
            f"(user_id={user_id}, event_type={event_type}, offset={offset}, limit={limit})"
        )

        # Initialize Service layer
        db_client = get_database_client()
        repository = SupabaseEventsRepository(db_client)
        service = EventsService(repository)

        # Service handles validation and calls Repository
        result = await service.get_user_events(
            user_id=user_id,
            event_type=event_type,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            limit=limit
        )

        return UserEventsResponse(**result)

    except ValueError as e:
        # Client error (400)
        logger.warning(f"[Admin {admin.get('id')}] Invalid parameters: {e}")
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        # Server error (500)
        logger.error(f"[Admin {admin.get('id')}] Get user events failed: {type(e).__name__} - {e}")
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
    try:
        logger.info(
            f"[Admin {admin.get('id')}] Getting event stats "
            f"(group_by={group_by}, start_date={start_date}, end_date={end_date})"
        )

        # Initialize Service layer
        db_client = get_database_client()
        repository = SupabaseEventsRepository(db_client)
        service = EventsService(repository)

        # Service handles validation and calls Repository
        stats = await service.get_event_stats(
            start_date=start_date,
            end_date=end_date,
            group_by=group_by
        )

        return EventStatsResponse(
            stats=stats,
            group_by=group_by,
            start_date=start_date,
            end_date=end_date
        )

    except ValueError as e:
        # Client error (400)
        logger.warning(f"[Admin {admin.get('id')}] Invalid parameters: {e}")
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        # Server error (500)
        logger.error(f"[Admin {admin.get('id')}] Get event stats failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve event statistics")


# ==========================================
# Aggregated Stats Endpoints
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
    Supported types: daily_active_users, hourly_active_users, daily_events, hourly_events
    """
    try:
        logger.info(
            f"[Admin {admin.get('id')}] Getting aggregated stats "
            f"(stat_type={stat_type}, use_cache={use_cache})"
        )

        # Initialize Service layer
        db_client = get_database_client()
        repository = SupabaseEventsRepository(db_client)
        service = EventsService(repository)

        # Service handles validation and calls Repository
        aggregated_stats = await service.get_aggregated_stats(
            stat_type=stat_type,
            use_cache=use_cache
        )

        if aggregated_stats is None:
            return AggregatedStatsResponse(
                data=None,
                message="No cached data available. Run aggregation task first."
            )

        return AggregatedStatsResponse(data=aggregated_stats.to_dict())

    except ValueError as e:
        # Client error (400)
        logger.warning(f"[Admin {admin.get('id')}] Invalid stat_type: {e}")
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        # Server error (500)
        logger.error(f"[Admin {admin.get('id')}] Get aggregated stats failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve aggregated statistics")


@router.get("/aggregated/{stat_type}/range", response_model=AggregatedStatsRangeResponse)
@limiter.limit("30/minute")
async def adm_get_aggregated_stats_range(
    request: Request,
    stat_type: str,
    days: int = Query(30, ge=1, le=MAX_RANGE_DAYS, description=f"Number of days (1-{MAX_RANGE_DAYS})"),
    admin: dict = Depends(require_admin)
):
    """Fetch aggregated stats over a specific number of days."""
    try:
        logger.info(
            f"[Admin {admin.get('id')}] Getting aggregated stats range "
            f"(stat_type={stat_type}, days={days})"
        )

        # Initialize Service layer
        db_client = get_database_client()
        repository = SupabaseEventsRepository(db_client)
        service = EventsService(repository)

        # Service handles validation and calls Repository
        stats_list = await service.get_aggregated_stats_range(
            stat_type=stat_type,
            days=days
        )

        return AggregatedStatsRangeResponse(
            stats=[stat.to_dict() for stat in stats_list],
            stat_type=stat_type,
            days=days
        )

    except ValueError as e:
        # Client error (400)
        logger.warning(f"[Admin {admin.get('id')}] Invalid parameters: {e}")
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        # Server error (500)
        logger.error(f"[Admin {admin.get('id')}] Get aggregated stats range failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve aggregated statistics range")


@router.post("/aggregation/run", response_model=AggregationTriggerResponse)
@limiter.limit("5/minute")
async def adm_run_aggregation(
    request: Request,
    task_type: str = Query("all", description="Task type: all, hourly, daily"),
    admin: dict = Depends(require_admin)
):
    """
    Manually trigger aggregation task (task_type: all | hourly | daily).

    TODO (EVT-CRITICAL-2): Refactor to use Service layer instead of direct scheduler call
    """
    # Validate task_type
    if task_type not in VALID_TASK_TYPES:
        raise HTTPException(
            400,
            f"Invalid task_type '{task_type}'. Must be one of: {', '.join(VALID_TASK_TYPES)}"
        )

    try:
        logger.info(f"[Admin {admin.get('id')}] Manually triggered aggregation: {task_type}")

        # TODO: Replace with Service call
        # Currently calling scheduler directly (EVT-CRITICAL-2)
        result = run_aggregation_now(task_type)

        # Ensure result conforms to response model
        if isinstance(result, dict):
            return AggregationTriggerResponse(
                status=result.get("status", "completed"),
                task_type=task_type,
                message=result.get("message"),
                details=result
            )
        else:
            return AggregationTriggerResponse(
                status="completed",
                task_type=task_type,
                details={"result": str(result)}
            )

    except ValueError as e:
        # Client error (400)
        logger.warning(f"[Admin {admin.get('id')}] Invalid task_type: {e}")
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        # Server error (500)
        logger.error(f"[Admin {admin.get('id')}] Run aggregation failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to run aggregation task")
