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

from fastapi import APIRouter, Depends, Request, Path
from pydantic import BaseModel

from domains.identity.aggregates.user_profile import UserProfile
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
    task_id: str = Path(..., description="Task ID to query (UUID format)"),
    user: UserProfile = Depends(get_current_user),
) -> TaskStatusResponse:
    """
    Get background task status and progress.

    Retrieves real-time status information for asynchronous tasks such as AI image
    generation, Smart Scan processing, PDF/ZIP exports, and batch operations.
    Supports polling for task completion and progress bar updates.

    v3.0.0: Uses GetTaskStatusHandler (CQRS Query pattern).

    Args:
        task_id: Task ID to query (UUID string)
            Format: "550e8400-e29b-41d4-a716-446655440000"
            Obtained from task creation endpoints (e.g., POST /generations)

    Returns:
        TaskStatusResponse containing:
            - id: Task ID (echoed back)
            - status: Task status (one of):
                - "pending": Waiting in queue
                - "queued": Accepted by queue, waiting for worker
                - "processing": Currently being processed by worker
                - "completed": Successfully finished
                - "failed": Failed with error
                - "cancelled": Cancelled by user
            - progress: Progress percentage (0-100)
            - current_step: Current step number (e.g., 2)
            - total_steps: Total steps in task (e.g., 8 for 8 page generation)
            - message: Human-readable status message
                Examples: "Generating page 3 of 8", "Completed successfully"
            - result: Task result when completed (null until done)
                For image generation: {"images": ["url1", "url2", ...]}
                For exports: {"download_url": "...", "expires_at": "..."}
            - error: Error message if failed (null otherwise)
            - created_at: Task creation timestamp
            - updated_at: Last status update timestamp
            - estimated_time_seconds: Estimated time to completion (if available)

    Raises:
        404: Task not found or belongs to different user
        401: Unauthorized (not authenticated)
        429: Rate limit exceeded (max 60 requests per minute)
        500: Database error or service unavailable

    Security:
        - Authentication required
        - User can only access their own tasks
        - Rate limit: 60 requests per minute (for polling)
        - Task ID is UUID (hard to guess)

    Usage:
        Used by frontend for:
        - Polling task status every 2-3 seconds
        - Updating progress bars
        - Displaying completion notifications
        - Retrieving generated images/export files

    Example:
        GET /api/v2/user/tasks/550e8400-e29b-41d4-a716-446655440000

        Response (in progress):
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "processing",
            "progress": 37,
            "current_step": 3,
            "total_steps": 8,
            "message": "Generating page 3 of 8",
            "result": null,
            "error": null,
            "created_at": "2026-01-11T10:30:00Z",
            "updated_at": "2026-01-11T10:30:15Z",
            "estimated_time_seconds": 25
        }

        Response (completed):
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "completed",
            "progress": 100,
            "current_step": 8,
            "total_steps": 8,
            "message": "Completed successfully",
            "result": {
                "images": [
                    "https://storage.example.com/gen_abc123_page1.png",
                    "https://storage.example.com/gen_abc123_page2.png"
                ]
            },
            "error": null,
            "created_at": "2026-01-11T10:30:00Z",
            "updated_at": "2026-01-11T10:30:45Z"
        }
    """
    container = get_container()
    handler = await container.get_task_status_handler()

    query = GetTaskStatusQuery(
        task_id=task_id,
        user_id=user.user_id,
    )

    result = await handler.handle(query)

    return TaskStatusResponse(**result.task_data)


@router.post("/{task_id}/cancel")
@limiter.limit("10/minute")
async def cancel_task(
    request: Request,
    task_id: str = Path(..., description="Task ID to cancel (UUID format)"),
    user: UserProfile = Depends(get_current_user),
) -> TaskCancelResponse:
    """
    Cancel a pending or queued background task.

    Allows users to cancel tasks that haven't started processing yet. Useful for
    correcting mistakes (wrong prompt, accidental submission) or freeing up queue
    slots. Credits are automatically refunded for successfully cancelled tasks.

    v3.0.0: Uses CancelTaskHandler (CQRS Command pattern).

    Args:
        task_id: Task ID to cancel (UUID string)
            Format: "550e8400-e29b-41d4-a716-446655440000"
            Must be a task owned by the authenticated user

    Returns:
        TaskCancelResponse containing:
            - success: true if task was cancelled
            - message: Confirmation message
            - refunded_credits: Number of credits refunded (if applicable)
                AI image generation: 5 credits refunded
                AI text generation: 1 credit refunded
                Smart Scan: 10 credits refunded
                Export tasks: 0 credits (free)

    Raises:
        400: Task cannot be cancelled (already processing, completed, or failed)
            Only "pending" and "queued" tasks can be cancelled
        404: Task not found or belongs to different user
        401: Unauthorized (not authenticated)
        429: Rate limit exceeded (max 10 requests per minute)
        500: Database error or queue service unavailable

    Security:
        - Authentication required
        - User can only cancel their own tasks
        - Rate limit: 10 requests per minute
        - Task ID is UUID (hard to guess)
        - Atomic credit refund (transaction guaranteed)

    Behavior:
        - Task status changes to "cancelled"
        - Credits are refunded to user's balance
        - Task is removed from worker queue
        - Partial results (if any) are discarded
        - Cannot cancel tasks that are already processing

    Example:
        POST /api/v2/user/tasks/550e8400-e29b-41d4-a716-446655440000/cancel

        Response (success):
        {
            "success": true,
            "message": "Task cancelled successfully",
            "refunded_credits": 5
        }

        Response (error - already processing):
        {
            "success": false,
            "message": "Cannot cancel task that is already processing",
            "refunded_credits": 0
        }
    """
    container = get_container()
    handler = await container.get_cancel_task_handler()

    command = CancelTaskCommand(
        task_id=task_id,
        user_id=user.user_id,
    )

    result = await handler.handle(command)

    return TaskCancelResponse(**result.result_data)
