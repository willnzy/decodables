"""Tasks API - Background tasks endpoints (v3).

@module api.user.tasks
@version 3.0.0

Changes:
- v3.0.0: DDD architecture upgrade - CQRS Query/Command pattern
  - Created TasksService with task status/cancellation business logic
  - Added GetTaskStatusHandler (Query Handler)
  - Added CancelTaskHandler (Command Handler)
  - Eliminated direct infrastructure calls from API layer
  - Moved all validation and business logic to Service layer
  - Improved testability and maintainability

- v2.1.0: Security improvements
  - T-MEDIUM-1: Added task_id format validation (3-64 chars, alphanumeric/hyphen/underscore)
  - T-LOW-1: Added "scheduled" to cancellable status list

Endpoints:
- GET /api/v2/user/tasks/{task_id} - Get task status
- POST /api/v2/user/tasks/{task_id}/cancel - Cancel a task
"""

from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from dependencies import get_current_user
from container import get_container
from application.queries.tasks import GetTaskStatusQuery, CancelTaskCommand
from infrastructure.rate_limiter import limiter

router = APIRouter(prefix="/tasks", tags=["user-tasks-v3"])


# ==========================================
# Response Models
# ==========================================

class TaskStatusResponse(BaseModel):
    """Task status response."""
    task_id: str
    status: str  # pending, queued, processing, completed, failed, cancelled
    progress: int = 0
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None

    class Config:
        extra = "allow"


class TaskCancelResponse(BaseModel):
    """Task cancel response."""
    status: str
    task_id: str
    credits_refunded: int = 0
    message: str


# ==========================================
# Endpoints
# ==========================================

@router.get("/{task_id}")
@limiter.limit("60/minute")
async def get_task_status(
    request: Request,
    task_id: str,
    user: dict = Depends(get_current_user),
) -> TaskStatusResponse:
    """
    Get task status and progress.

    v3.0.0: Now uses GetTaskStatusHandler (CQRS Query pattern).

    Returns:
        - status: pending, queued, processing, completed, failed, cancelled
        - progress: 0-100
        - current_step/total_steps: for progress bar
        - result: image URLs when completed
        - error: error message if failed
    """
    container = get_container()
    handler = container.get_task_status_handler

    query = GetTaskStatusQuery(
        task_id=task_id,
        user_id=user["id"],
    )

    result = await handler.handle(query)

    return TaskStatusResponse(**result.task_data)


@router.post("/{task_id}/cancel")
@limiter.limit("10/minute")
async def cancel_task(
    request: Request,
    task_id: str,
    user: dict = Depends(get_current_user),
) -> TaskCancelResponse:
    """
    Cancel a pending or queued task.

    v3.0.0: Now uses CancelTaskHandler (CQRS Command pattern).

    Only tasks that haven't started processing can be cancelled.
    Credits will be refunded for cancelled tasks.
    """
    container = get_container()
    handler = container.cancel_task_handler

    command = CancelTaskCommand(
        task_id=task_id,
        user_id=user["id"],
    )

    result = await handler.handle(command)

    return TaskCancelResponse(**result.result_data)
