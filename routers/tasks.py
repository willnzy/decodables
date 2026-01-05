"""
Tasks Router - Task queue status and management endpoints

@module routers.tasks
@version 3.24

Endpoints:
- GET /api/tasks/{task_id} - Get task status
- POST /api/tasks/{task_id}/cancel - Cancel a task
- GET /api/admin/queue/stats - Queue statistics (admin)
- WS /ws/task/{task_id} - WebSocket for real-time updates
"""

import logging
from fastapi import APIRouter, HTTPException, Request, Depends, WebSocket

from services.db_service import supabase, add_credits
from services.task_queue import task_queue, progress_tracker
from services.websocket import ws_manager
from services.rate_limiter import limiter
from dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["tasks"])


# ==========================================
# Task Status API (v3.23)
# ==========================================

@router.get("/api/tasks/{task_id}")
@limiter.limit("60/minute")
async def get_task_status(request: Request, task_id: str, user: dict = Depends(get_current_user)):
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
                "p_user_id": user["id"]
            }).execute()
            
            if result.data and result.data.get("success"):
                return result.data
        except Exception as e:
            logger.warning(f"Failed to get task from DB: {e}")
        
        raise HTTPException(404, "Task not found")
    
    return status


@router.post("/api/tasks/{task_id}/cancel")
@limiter.limit("10/minute")
async def cancel_task(request: Request, task_id: str, user: dict = Depends(get_current_user)):
    """
    Cancel a pending or queued task.
    
    Only tasks that haven't started processing can be cancelled.
    Credits will be refunded for cancelled tasks.
    """
    # Check task ownership and status
    status = progress_tracker.get_status(task_id)
    
    if not status:
        raise HTTPException(404, "Task not found")
    
    if status.get("status") not in ("pending", "queued"):
        raise HTTPException(400, f"Cannot cancel task in '{status.get('status')}' status")
    
    # Attempt cancellation
    if task_queue.cancel_task(task_id, user["id"]):
        # Get task params for refund
        try:
            result = supabase.table("generation_tasks").select("params").eq(
                "task_id", task_id
            ).eq("user_id", user["id"]).single().execute()
            
            if result.data:
                credits_charged = result.data.get("params", {}).get("credits_charged", 0)
                if credits_charged > 0:
                    add_credits(user["id"], credits_charged, "refund", f"Cancelled task {task_id}")
                    
                    return {
                        "status": "cancelled",
                        "task_id": task_id,
                        "credits_refunded": credits_charged,
                        "message": "Task cancelled and credits refunded"
                    }
        except Exception as e:
            logger.warning(f"Failed to refund credits for cancelled task: {e}")
        
        return {
            "status": "cancelled",
            "task_id": task_id,
            "message": "Task cancelled"
        }
    
    raise HTTPException(400, "Failed to cancel task")


# ==========================================
# Queue Stats API (Admin) (v3.23)
# ==========================================

@router.get("/api/admin/queue/stats")
@limiter.limit("30/minute")
async def get_queue_stats(request: Request, user: dict = Depends(get_current_user)):
    """
    Get task queue statistics (admin only).
    """
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin access required")
    
    queue_stats = task_queue.get_queue_stats()
    ws_stats = ws_manager.get_stats()
    
    return {
        "queue": queue_stats,
        "websocket": ws_stats,
    }


# ==========================================
# WebSocket for Real-time Task Progress (v3.23)
# ==========================================

@router.websocket("/ws/task/{task_id}")
async def task_websocket(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint for real-time task progress updates.
    
    Messages sent to client:
    - {"type": "status", ...}: Current task status
    - {"type": "progress", ...}: Progress update with percentage
    - {"type": "completed", ...}: Task completed with result
    - {"type": "failed", ...}: Task failed with error
    - {"type": "heartbeat", ...}: Keep-alive ping
    
    Messages from client:
    - {"type": "ping"}: Heartbeat request
    - {"type": "cancel"}: Request task cancellation
    """
    await ws_manager.handle_task_connection(websocket, task_id)
