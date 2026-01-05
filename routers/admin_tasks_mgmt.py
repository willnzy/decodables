"""
Admin Tasks Management Router - Background task management

@module routers.admin_tasks_mgmt
@version 3.24

Endpoints:
- GET /api/admin/tasks/status - Get task status
- GET /api/admin/tasks/logs - Get task logs
- GET /api/admin/tasks/health - Get task health
- POST /api/admin/tasks/{task_name}/run - Run task manually
"""

import logging
from typing import Optional
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Depends

from dependencies import require_admin
from services.db_service import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/tasks", tags=["admin-tasks"])


# ==========================================
# Task Management Routes
# ==========================================

@router.get("/status")
def get_tasks_status(admin: dict = Depends(require_admin)):
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
        return {"tasks": {}, "error": str(e)}


@router.get("/logs")
def get_task_logs(
    task_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    admin: dict = Depends(require_admin)
):
    """Get task execution logs."""
    try:
        query = supabase.table("scheduled_task_logs").select("*")
        
        if task_name:
            query = query.eq("task_name", task_name)
        if status:
            query = query.eq("status", status)
        
        result = query.order("started_at", desc=True).limit(limit).execute()
        return {"logs": result.data or []}
    except Exception as e:
        return {"logs": [], "error": str(e)}


@router.get("/health")
def get_tasks_health(admin: dict = Depends(require_admin)):
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
        return {"status": "error", "error": str(e)}


@router.post("/{task_name}/run")
def run_task_manually(task_name: str, admin: dict = Depends(require_admin)):
    """Manually trigger a scheduled task."""
    from scheduler import run_aggregation_now
    
    valid_tasks = ["hourly", "daily", "all", "cleanup", "retention"]
    
    if task_name not in valid_tasks:
        raise HTTPException(400, f"Invalid task. Valid tasks: {valid_tasks}")
    
    try:
        result = run_aggregation_now(task_name)
        return {"status": "triggered", "task": task_name, "result": result}
    except Exception as e:
        raise HTTPException(500, f"Failed to run task: {str(e)}")
