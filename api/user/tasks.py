"""Tasks API - Background tasks endpoints (v2).

@module api.user.tasks
@version 2.0.0

Endpoints:
- GET /api/v2/user/tasks/{task_id} - Get task status
- POST /api/v2/user/tasks/{task_id}/cancel - Cancel a task
"""

import logging
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from dependencies import get_current_user
from services.db_service import supabase, add_credits
from services.task_queue import task_queue, progress_tracker
from services.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/user/tasks", tags=["user-tasks-v2"])


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

    Returns:
        - status: pending, queued, processing, completed, failed, cancelled
        - progress: 0-100
        - current_step/total_steps: for progress bar
        - result: image URLs when completed
        - error: error message if failed
    """
    # Get status from progress tracker (Redis)
    status = progress_tracker.get_status(task_id)

    if not status:
        # Try database as fallback
        try:
            result = supabase.rpc("get_task_details", {
                "p_task_id": task_id,
                "p_user_id": user["id"],
            }).execute()

            if result.data and result.data.get("success"):
                data = result.data
                return TaskStatusResponse(
                    task_id=task_id,
                    status=data.get("status", "unknown"),
                    progress=data.get("progress", 0),
                    current_step=data.get("current_step"),
                    total_steps=data.get("total_steps"),
                    message=data.get("message"),
                    result=data.get("result"),
                    error=data.get("error"),
                    created_at=data.get("created_at"),
                    completed_at=data.get("completed_at"),
                )
        except Exception as e:
            logger.warning(f"Failed to get task from DB: {e}")

        raise HTTPException(404, "Task not found")

    return TaskStatusResponse(
        task_id=task_id,
        status=status.get("status", "unknown"),
        progress=status.get("progress", 0),
        current_step=status.get("current_step"),
        total_steps=status.get("total_steps"),
        message=status.get("message"),
        result=status.get("result"),
        error=status.get("error"),
        created_at=status.get("created_at"),
        completed_at=status.get("completed_at"),
    )


@router.post("/{task_id}/cancel")
@limiter.limit("10/minute")
async def cancel_task(
    request: Request,
    task_id: str,
    user: dict = Depends(get_current_user),
) -> TaskCancelResponse:
    """
    Cancel a pending or queued task.

    Only tasks that haven't started processing can be cancelled.
    Credits will be refunded for cancelled tasks.
    """
    # Check task status
    status = progress_tracker.get_status(task_id)

    if not status:
        raise HTTPException(404, "Task not found")

    if status.get("status") not in ("pending", "queued"):
        raise HTTPException(
            400,
            f"Cannot cancel task in '{status.get('status')}' status",
        )

    # Attempt cancellation
    if task_queue.cancel_task(task_id, user["id"]):
        credits_refunded = 0

        # Get task params for refund
        try:
            result = supabase.table("generation_tasks").select("params").eq(
                "task_id", task_id,
            ).eq("user_id", user["id"]).single().execute()

            if result.data:
                credits_charged = result.data.get("params", {}).get("credits_charged", 0)
                if credits_charged > 0:
                    add_credits(user["id"], credits_charged, "refund", f"Cancelled task {task_id}")
                    credits_refunded = credits_charged

        except Exception as e:
            logger.warning(f"Failed to refund credits for cancelled task: {e}")

        return TaskCancelResponse(
            status="cancelled",
            task_id=task_id,
            credits_refunded=credits_refunded,
            message="Task cancelled" + (" and credits refunded" if credits_refunded else ""),
        )

    raise HTTPException(400, "Failed to cancel task")
