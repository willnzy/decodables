"""
Admin Events Router - Events and aggregation endpoints for admins

@module api.admin.events
@version 3.29 (Container-based DI)

Changes in v3.29:
- EVT-ARCH-1: Migrated to Container-based dependency injection
- EVT-ARCH-2: Removed direct repository imports from API layer
- Architecture: API → Container → Service → Repository (Strict DIP)

Changes in v3.27:
- EVT-CRITICAL-1: Created DDD three-layer architecture
- EVT-CRITICAL-2: API now calls Service instead of Repository directly
- EVT-HIGH-1: Migrated constants to Domain layer
- EVT-HIGH-4: Added @retry_on_network_error to get_user_events
- EVT-MEDIUM-1: Improved error handling (distinguish 400 vs 500)
- EVT-MEDIUM-2: Migrated validation logic to Domain Service

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

from infrastructure.rate_limiter import limiter
from scheduler import run_aggregation_now
from dependencies import require_admin

# v3.29: Container-based DI
# WHY: API layer should not know about concrete repository implementations
from container import get_container

from domains.events import (
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
# Dependency Injection (v3.29: Container-based)
# ==========================================

async def get_events_service():
    """
    Get EventsService from Container.

    WHY Container-based DI?
    1. Decouples API layer from infrastructure implementations
    2. Enables easy testing with mock services
    3. Centralizes dependency management
    4. Supports future provider switches
    """
    container = get_container()
    return await container.get_events_service()


# ==========================================
# Events Endpoints
# ==========================================

@router.get("/events", response_model=UserEventsResponse)
@limiter.limit("30/minute")
async def adm_get_user_events(
    request: Request,
    event_type: Optional[str] = Query(None, max_length=100, description="Filter by event type"),
    user_id: Optional[str] = Query(None, description="Filter by specific user ID"),
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD or ISO 8601)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD or ISO 8601)"),
    offset: int = Query(0, ge=0, description="Number of items to skip for pagination"),
    limit: int = Query(50, ge=1, le=MAX_LIMIT, description=f"Max items to return (1-{MAX_LIMIT})"),
    admin: dict = Depends(require_admin),
    service=Depends(get_events_service),
):
    """
    Get user events with optional filtering and pagination.

    v3.29: Refactored to use Container-based DI.
    """
    try:
        logger.info(
            f"[Admin {admin.get('id')}] Getting user events "
            f"(user_id={user_id}, event_type={event_type}, offset={offset}, limit={limit})"
        )

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
        logger.warning(f"[Admin {admin.get('id')}] Invalid parameters: {e}")
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Get user events failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve user events")


@router.get("/events/stats", response_model=EventStatsResponse)
@limiter.limit("30/minute")
async def adm_get_event_stats(
    request: Request,
    start_date: Optional[str] = Query(None, description="Start date filter"),
    end_date: Optional[str] = Query(None, description="End date filter"),
    group_by: str = Query("event_type", description="Grouping dimension: event_type, user_id, date, hour"),
    admin: dict = Depends(require_admin),
    service=Depends(get_events_service),
):
    """
    Get event statistics with flexible grouping and date filtering.

    v3.29: Refactored to use Container-based DI.
    """
    try:
        logger.info(
            f"[Admin {admin.get('id')}] Getting event stats "
            f"(group_by={group_by}, start_date={start_date}, end_date={end_date})"
        )

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
        logger.warning(f"[Admin {admin.get('id')}] Invalid parameters: {e}")
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
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
    admin: dict = Depends(require_admin),
    service=Depends(get_events_service),
):
    """
    Fetch aggregated stats for the given stat_type.

    v3.29: Refactored to use Container-based DI.
    """
    try:
        logger.info(
            f"[Admin {admin.get('id')}] Getting aggregated stats "
            f"(stat_type={stat_type}, use_cache={use_cache})"
        )

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
        logger.warning(f"[Admin {admin.get('id')}] Invalid stat_type: {e}")
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Get aggregated stats failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve aggregated statistics")


@router.get("/aggregated/{stat_type}/range", response_model=AggregatedStatsRangeResponse)
@limiter.limit("30/minute")
async def adm_get_aggregated_stats_range(
    request: Request,
    stat_type: str,
    days: int = Query(30, ge=1, le=MAX_RANGE_DAYS, description=f"Number of days (1-{MAX_RANGE_DAYS})"),
    admin: dict = Depends(require_admin),
    service=Depends(get_events_service),
):
    """
    Fetch aggregated stats over a specific number of days.

    v3.29: Refactored to use Container-based DI.
    """
    try:
        logger.info(
            f"[Admin {admin.get('id')}] Getting aggregated stats range "
            f"(stat_type={stat_type}, days={days})"
        )

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
        logger.warning(f"[Admin {admin.get('id')}] Invalid parameters: {e}")
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Get aggregated stats range failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve aggregated statistics range")


@router.post("/aggregation/run", response_model=AggregationTriggerResponse)
@limiter.limit("5/minute")
async def adm_run_aggregation(
    request: Request,
    task_type: str = Query("all", description="Task type: all, hourly, daily"),
    admin: dict = Depends(require_admin),
):
    """
    Manually trigger aggregation task.

    Note: This endpoint directly calls scheduler, not via service,
    as it's a system operation rather than data retrieval.
    """
    # Validate task_type
    if task_type not in VALID_TASK_TYPES:
        raise HTTPException(
            400,
            f"Invalid task_type '{task_type}'. Must be one of: {', '.join(VALID_TASK_TYPES)}"
        )

    try:
        logger.info(f"[Admin {admin.get('id')}] Manually triggered aggregation: {task_type}")

        result = run_aggregation_now(task_type)

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
        logger.warning(f"[Admin {admin.get('id')}] Invalid task_type: {e}")
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Run aggregation failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to run aggregation task")
