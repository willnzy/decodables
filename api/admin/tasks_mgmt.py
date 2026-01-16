"""
Admin Tasks Management Router - Background task management

@module api.admin.tasks_mgmt
@version 3.29 (Container-based DI)

Changes in v3.29:
- TASK-ARCH-1: Migrated to Container-based dependency injection
- TASK-ARCH-2: Created AdminTasksService for business logic
- TASK-ARCH-3: Removed direct repository imports from API layer
- Architecture: API → Container → Service → Repository (Strict DIP)

Changes in v3.26:
- TASK-HIGH-1: 迁移到 Repository 层 (符合 DDD 架构)
- TASK-MEDIUM-1: 添加 Pydantic Request/Response 模型
- TASK-MEDIUM-2: GET /health 添加查询限制 (.limit(1000))
- TASK-MEDIUM-3: Repository 层添加 @retry_on_network_error 装饰器
- TASK-MEDIUM-4: 完善 cleanup/retention 任务逻辑

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
from infrastructure.rate_limiter import limiter

# v3.29: Container-based DI
# WHY: API layer should not know about concrete repository implementations
from container import get_container

from .tasks_models import (
    TaskStatusResponse,
    TaskLogsResponse,
    TaskHealthResponse,
    TaskTriggerResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks/management", tags=["admin-tasks-mgmt-v2"])


# ==========================================
# Dependency Injection (v3.29: Container-based)
# ==========================================

async def get_admin_tasks_service():
    """
    Get AdminTasksService from Container.

    WHY Container-based DI?
    1. Decouples API layer from infrastructure implementations
    2. Enables easy testing with mock services
    3. Centralizes dependency management
    4. Supports future provider switches
    """
    container = get_container()
    return await container.get_admin_tasks_service()


# ==========================================
# Constants
# ==========================================

# Valid task names (for path parameter validation)
VALID_TASK_NAMES = {"hourly", "daily", "all", "cleanup", "retention"}


# ==========================================
# Task Management Routes
# ==========================================

@router.get("/status", response_model=TaskStatusResponse)
@limiter.limit("30/minute")
async def get_tasks_status(
    request: Request,
    admin: dict = Depends(require_admin),
    service=Depends(get_admin_tasks_service),
):
    """
    Get status of all scheduled tasks.

    v3.29: Refactored to use AdminTasksService via Container.
    """
    try:
        return await service.get_task_status()
    except Exception as e:
        logger.error(f"[Admin] Get tasks status failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve task status")


@router.get("/logs", response_model=TaskLogsResponse)
@limiter.limit("30/minute")
async def get_task_logs(
    request: Request,
    task_name: Optional[str] = Query(None, max_length=50),
    status: Optional[str] = Query(None, max_length=20),
    limit: int = Query(100, ge=1, le=500, description="Number of records to return (1-500)"),
    admin: dict = Depends(require_admin),
    service=Depends(get_admin_tasks_service),
):
    """
    Get task execution logs.

    v3.29: Refactored to use AdminTasksService via Container.
    """
    try:
        return await service.get_task_logs(task_name, status, limit)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"[Admin] Get task logs failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve task logs")


@router.get("/health", response_model=TaskHealthResponse)
@limiter.limit("30/minute")
async def get_tasks_health(
    request: Request,
    admin: dict = Depends(require_admin),
    service=Depends(get_admin_tasks_service),
):
    """
    Get overall task health status.

    v3.29: Refactored to use AdminTasksService via Container.
    """
    try:
        return await service.get_tasks_health()
    except Exception as e:
        logger.error(f"[Admin] Get tasks health failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve task health status")


@router.post("/{task_name}/run", response_model=TaskTriggerResponse)
@limiter.limit("10/minute")
async def run_task_manually(
    request: Request,
    task_name: str,
    admin: dict = Depends(require_admin),
    service=Depends(get_admin_tasks_service),
):
    """
    Manually trigger a scheduled task.

    v3.29: Refactored to use AdminTasksService via Container.
    """
    # Validate task_name length
    if len(task_name) > 50:
        raise HTTPException(400, "Task name too long (max 50 characters)")

    # Validate task_name
    if task_name not in VALID_TASK_NAMES:
        raise HTTPException(400, f"Invalid task. Valid tasks: {', '.join(VALID_TASK_NAMES)}")

    try:
        result = service.run_task(task_name)
        logger.info(f"[Admin {admin.get('id')}] Manually triggered task: {task_name}")
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"[Admin] Run task manually failed for {task_name}: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to run task")
