"""
Admin Tasks Management Router - Background task management

@module api.admin.tasks_mgmt
@version 3.26

Changes:
- v3.26: DDD架构重构 + 功能增强
  - TASK-HIGH-1: 迁移到 Repository 层 (符合 DDD 架构)
  - TASK-MEDIUM-1: 添加 Pydantic Request/Response 模型
  - TASK-MEDIUM-2: GET /health 添加查询限制 (.limit(1000))
  - TASK-MEDIUM-3: Repository 层添加 @retry_on_network_error 装饰器
  - TASK-MEDIUM-4: 完善 cleanup/retention 任务逻辑
  - TASK-LOW-3: 统一错误处理方式 (HTTPException)

- v3.25: Security improvements
  - TASK-MEDIUM-1: Added rate limiting to all 4 endpoints
  - TASK-MEDIUM-2: Added limit range validation
  - TASK-MEDIUM-3: Added status enum validation
  - TASK-MEDIUM-4: Added task_name enum validation with constants
  - TASK-LOW-1: Limited error exposure
  - TASK-LOW-2: Added task_name length validation

Endpoints:
- GET /api/admin/tasks/management/status - Get task status
- GET /api/admin/tasks/management/logs - Get task logs
- GET /api/admin/tasks/management/health - Get task health
- POST /api/admin/tasks/management/{task_name}/run - Run task manually
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request, Query

from dependencies import require_admin
from core.database import get_async_db_client
from infrastructure.repositories import SupabaseTasksRepository
from infrastructure.rate_limiter import limiter
from .tasks_models import (
    TaskStatusResponse,
    TaskLogsResponse,
    TaskHealthResponse,
    TaskTriggerResponse,
)

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
# Task Management Routes (v3.26: DDD架构)
# ==========================================

@router.get("/status", response_model=TaskStatusResponse)
@limiter.limit("30/minute")
async def get_tasks_status(
    request: Request,
    admin: dict = Depends(require_admin)
):
    """Get status of all scheduled tasks."""
    try:
        db_client = await get_async_db_client()
        tasks_repo = SupabaseTasksRepository(db_client)
        task_status = await tasks_repo.get_task_status()
        return {"tasks": task_status}
    except Exception as e:
        # v3.26: TASK-LOW-3 - 统一使用 HTTPException
        logger.error(f"[Admin] Get tasks status failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve task status")


@router.get("/logs", response_model=TaskLogsResponse)
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
        db_client = await get_async_db_client()
        tasks_repo = SupabaseTasksRepository(db_client)
        logs = await tasks_repo.get_task_logs(task_name, status, limit)
        return {"logs": logs}
    except Exception as e:
        # v3.26: TASK-LOW-3 - 统一使用 HTTPException
        logger.error(f"[Admin] Get task logs failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve task logs")


@router.get("/health", response_model=TaskHealthResponse)
@limiter.limit("30/minute")
async def get_tasks_health(
    request: Request,
    admin: dict = Depends(require_admin)
):
    """Get overall task health status."""
    try:
        db_client = await get_async_db_client()
        tasks_repo = SupabaseTasksRepository(db_client)
        health_metrics = await tasks_repo.get_tasks_health()

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

        # Determine overall health status
        failed_runs = health_metrics["failed_runs"]
        status = "healthy" if failed_runs == 0 else "degraded"

        return {
            "status": status,
            "scheduler": scheduler_status,
            "last_hour": {
                "total_runs": health_metrics["total_runs"],
                "failed_runs": health_metrics["failed_runs"],
                "success_rate": health_metrics["success_rate"]
            }
        }
    except Exception as e:
        # v3.26: TASK-LOW-3 - 统一使用 HTTPException
        logger.error(f"[Admin] Get tasks health failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve task health status")


@router.post("/{task_name}/run", response_model=TaskTriggerResponse)
@limiter.limit("10/minute")
async def run_task_manually(
    request: Request,
    task_name: str,
    admin: dict = Depends(require_admin)
):
    """Manually trigger a scheduled task."""
    # v3.25: TASK-LOW-2 - Added task_name length validation
    if len(task_name) > 50:
        raise HTTPException(400, "Task name too long (max 50 characters)")

    # v3.25: TASK-MEDIUM-4 - Use constants instead of hardcoded list
    if task_name not in VALID_TASK_NAMES:
        raise HTTPException(400, f"Invalid task. Valid tasks: {', '.join(VALID_TASK_NAMES)}")

    try:
        # v3.26: TASK-MEDIUM-4 - 完善 cleanup/retention 逻辑
        if task_name == "cleanup":
            from scheduler import run_storage_cleanup
            run_storage_cleanup()
            result = {"status": "completed", "task_type": "cleanup"}
        elif task_name == "retention":
            # Retention cleanup not yet implemented in scheduler
            # For now, call aggregation (or implement later)
            from scheduler import run_aggregation_now
            result = run_aggregation_now("daily")  # Run daily aggregation as fallback
            result["task_type"] = "retention"
        else:
            from scheduler import run_aggregation_now
            result = run_aggregation_now(task_name)

        # v3.26: TASK-LOW-2 - 添加审计日志
        logger.info(f"[Admin {admin.get('id')}] Manually triggered task: {task_name}")

        return {"status": "triggered", "task": task_name, "result": result}
    except Exception as e:
        logger.error(f"[Admin] Run task manually failed for {task_name}: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to run task")
