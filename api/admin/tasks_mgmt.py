"""
Admin Tasks Management Router - Background task management

@module api.admin.tasks_mgmt
@version 3.25

Changes:
- v3.25: Security improvements
  - TASK-MEDIUM-1: Added rate limiting to all 4 endpoints
  - TASK-MEDIUM-2: Added limit range validation
  - TASK-MEDIUM-3: Added status enum validation
  - TASK-MEDIUM-4: Added task_name enum validation with constants
  - TASK-LOW-1: Limited error exposure
  - TASK-LOW-2: Added task_name length validation

Endpoints:
- GET /api/admin/tasks/status - Get task status
- GET /api/admin/tasks/logs - Get task logs
- GET /api/admin/tasks/health - Get task health
- POST /api/admin/tasks/{task_name}/run - Run task manually
"""

import logging
from typing import Optional
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Depends, Request, Query

from dependencies import require_admin
from core.database import get_supabase_client
from infrastructure.rate_limiter import limiter

supabase = get_supabase_client()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks/management", tags=["admin-tasks-mgmt-v2"])


# ==========================================
# Constants (v3.25)
# ==========================================

# v3.25: TASK-MEDIUM-3 - Valid task statuses
VALID_TASK_STATUSES = {"success", "failed", "running", "pending"}

# v3.25: TASK-MEDIUM-4 - Valid task names
VALID_TASK_NAMES = {"hourly", "daily", "all", "cleanup", "retention"}


# ==========================================
# Task Management Routes
# ==========================================

@router.get("/status")
@limiter.limit("30/minute")
async def get_tasks_status(request: Request, admin: dict = Depends(require_admin)):
    """Get status of all scheduled tasks."""
    try:
        result = supabase.table("scheduled_task_logs").select("*").order("started_at", desc=True).limit(50).execute()

        task_status = {}
        for log in (result.data or []):
            name = log.get("task_name")
            if name not in task_status:
                task_status[name] = {
                    "last_run": log.get("started_at"),
                    "last_status": log.get("status"),
                    "last_duration_ms": log.get("duration_ms"),
                    "last_error": log.get("error_message"),
                    "recent_runs": []
                }
            if len(task_status[name]["recent_runs"]) < 5:
                task_status[name]["recent_runs"].append({
                    "started_at": log.get("started_at"),
                    "status": log.get("status"),
                    "duration_ms": log.get("duration_ms")
                })

        return {"tasks": task_status}
    except Exception as e:
        # v3.25: TASK-LOW-1 - Limited error exposure
        logger.error(f"[Admin] Get tasks status failed: {e}")
        return {"tasks": {}, "error": "Failed to retrieve task status"}


@router.get("/logs")
@limiter.limit("30/minute")
async def get_task_logs(
    request: Request,
    task_name: Optional[str] = Query(None, max_length=50),
    status: Optional[str] = Query(None, max_length=20),
    # v3.25: TASK-MEDIUM-2 - Added limit range validation
    limit: int = Query(100, ge=1, le=500, description="Number of records to return (1-500)"),
    admin: dict = Depends(require_admin)
):
    """Get task execution logs."""
    # v3.25: TASK-MEDIUM-3 - Validate status enum
    if status is not None and status not in VALID_TASK_STATUSES:
        raise HTTPException(400, f"Invalid status. Must be one of: {', '.join(VALID_TASK_STATUSES)}")

    # v3.25: TASK-MEDIUM-4 - Validate task_name enum
    if task_name is not None and task_name not in VALID_TASK_NAMES:
        raise HTTPException(400, f"Invalid task_name. Must be one of: {', '.join(VALID_TASK_NAMES)}")

    try:
        query = supabase.table("scheduled_task_logs").select("*")

        if task_name:
            query = query.eq("task_name", task_name)
        if status:
            query = query.eq("status", status)

        result = query.order("started_at", desc=True).limit(limit).execute()
        return {"logs": result.data or []}
    except Exception as e:
        # v3.25: TASK-LOW-1 - Limited error exposure
        logger.error(f"[Admin] Get task logs failed: {e}")
        return {"logs": [], "error": "Failed to retrieve task logs"}


@router.get("/health")
@limiter.limit("30/minute")
async def get_tasks_health(request: Request, admin: dict = Depends(require_admin)):
    """Get overall task health status."""
    try:
        now = datetime.now(timezone.utc)
        last_hour = (now - timedelta(hours=1)).isoformat()

        result = supabase.table("scheduled_task_logs").select("task_name, status").gte("started_at", last_hour).execute()

        total = len(result.data or [])
        failed = sum(1 for log in (result.data or []) if log.get("status") == "failed")

        # Check scheduler status
        scheduler_status = "unknown"
        try:
            from scheduler import scheduler
            if scheduler and scheduler.running:
                scheduler_status = "running"
            else:
                scheduler_status = "stopped"
        except:
            pass

        return {
            "status": "healthy" if failed == 0 else "degraded",
            "scheduler": scheduler_status,
            "last_hour": {
                "total_runs": total,
                "failed_runs": failed,
                "success_rate": round((total - failed) / total * 100, 2) if total > 0 else 100
            }
        }
    except Exception as e:
        # v3.25: TASK-LOW-1 - Limited error exposure
        logger.error(f"[Admin] Get tasks health failed: {e}")
        return {"status": "error", "error": "Failed to retrieve task health status"}


@router.post("/{task_name}/run")
@limiter.limit("10/minute")
async def run_task_manually(request: Request, task_name: str, admin: dict = Depends(require_admin)):
    """Manually trigger a scheduled task."""
    # v3.25: TASK-LOW-2 - Added task_name length validation
    if len(task_name) > 50:
        raise HTTPException(400, "Task name too long (max 50 characters)")

    # v3.25: TASK-MEDIUM-4 - Use constants instead of hardcoded list
    if task_name not in VALID_TASK_NAMES:
        raise HTTPException(400, f"Invalid task. Valid tasks: {', '.join(VALID_TASK_NAMES)}")

    try:
        from scheduler import run_aggregation_now
        result = run_aggregation_now(task_name)
        return {"status": "triggered", "task": task_name, "result": result}
    except Exception as e:
        # v3.25: TASK-LOW-1 - Limited error exposure
        logger.error(f"[Admin] Run task manually failed for {task_name}: {e}")
        raise HTTPException(500, "Failed to run task")
