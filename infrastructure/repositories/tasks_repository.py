"""
Tasks Repository - Data access layer for tasks management.

@module infrastructure.repositories.tasks_repository
@version 2.1.0 (AsyncClient migration)

Changes in v2.1.0:
- Migrated all methods to use AsyncClient with await
- All .execute() calls now properly awaited

Changes in v2.0.0:
- Added SupabaseUserTasksRepository for user background tasks
- Existing SupabaseTasksRepository for admin scheduled tasks

This module provides database access methods for:
1. Admin scheduled tasks (cron jobs, monitoring)
2. User background tasks (generation tasks, async operations)
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from core.database import retry_on_network_error

logger = logging.getLogger(__name__)


class TasksRepository(ABC):
    """Abstract interface for tasks data access."""

    @abstractmethod
    async def get_task_status(self) -> Dict[str, Any]:
        """Get status of all scheduled tasks."""
        pass

    @abstractmethod
    async def get_task_logs(
        self,
        task_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get task execution logs with optional filters."""
        pass

    @abstractmethod
    async def get_tasks_health(self) -> Dict[str, Any]:
        """Get overall task health status."""
        pass


class SupabaseTasksRepository(TasksRepository):
    """Supabase implementation of TasksRepository."""

    def __init__(self, client):
        """
        Initialize repository with Supabase client.

        Args:
            client: Supabase client instance
        """
        self.client = client

    @retry_on_network_error()
    async def get_task_status(self) -> Dict[str, Any]:
        """
        Get status of all scheduled tasks.

        Returns:
            Dict with task status aggregated by task name:
            {
                "task_name": {
                    "last_run": "ISO timestamp",
                    "last_status": "success|failed|running|pending",
                    "last_duration_ms": int,
                    "last_error": str or None,
                    "recent_runs": [...]
                }
            }
        """
        # TASK-MEDIUM-2: Added .limit(50) to prevent excessive data
        result = await self.client.table("scheduled_task_logs")\
            .select("*")\
            .order("started_at", desc=True)\
            .limit(50)\
            .execute()

        # Aggregate by task name
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

        return task_status

    @retry_on_network_error()
    async def get_task_logs(
        self,
        task_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get task execution logs with optional filters.

        Args:
            task_name: Optional task name filter
            status: Optional status filter
            limit: Maximum number of logs to return (1-500)

        Returns:
            List of task log entries
        """
        query = self.client.table("scheduled_task_logs").select("*")

        if task_name:
            query = query.eq("task_name", task_name)
        if status:
            query = query.eq("status", status)

        result = await query.order("started_at", desc=True).limit(limit).execute()
        return result.data or []

    @retry_on_network_error()
    async def get_tasks_health(self) -> Dict[str, Any]:
        """
        Get overall task health status.

        Returns:
            Dict with health metrics:
            {
                "total_runs": int,
                "failed_runs": int,
                "success_rate": float,
                "period_start": "ISO timestamp"
            }
        """
        now = datetime.now(timezone.utc)
        last_hour = (now - timedelta(hours=1)).isoformat()

        # TASK-MEDIUM-2: Added .limit(1000) to prevent OOM
        result = await self.client.table("scheduled_task_logs")\
            .select("task_name, status")\
            .gte("started_at", last_hour)\
            .limit(1000)\
            .execute()

        total = len(result.data or [])
        failed = sum(1 for log in (result.data or []) if log.get("status") == "failed")

        return {
            "total_runs": total,
            "failed_runs": failed,
            "success_rate": round((total - failed) / total * 100, 2) if total > 0 else 100.0,
            "period_start": last_hour
        }


# ==========================================
# User Background Tasks Repository (v2.0.0)
# ==========================================

class SupabaseUserTasksRepository:
    """
    Supabase implementation for user background tasks.

    Handles data access for async user operations like:
    - Image generation tasks
    - PDF generation tasks
    - Story generation tasks
    - Export tasks
    """

    def __init__(self, supabase_client):
        """
        Initialize with Supabase client.

        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client

    @retry_on_network_error()
    async def get_task_from_database(
        self,
        task_id: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get task details from database (fallback when not in cache).

        Args:
            task_id: Task identifier (UUID)
            user_id: User ID (for ownership verification)

        Returns:
            Task details dict or None if not found
        """
        try:
            result = await self.supabase.table("generation_tasks").select(
                "*"
            ).eq("id", task_id).eq("user_id", user_id).limit(1).execute()

            if result is not None and result.data:
                return {"success": True, "task": result.data[0]}

            return None

        except Exception as e:
            logger.warning(f"Failed to get task from database: {e}")
            return None

    @retry_on_network_error()
    async def get_task_params(
        self,
        task_id: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get task parameters from generation_tasks table (for credit refund lookup).

        Args:
            task_id: Task identifier
            user_id: User ID (for ownership verification)

        Returns:
            Task params dict or None if not found
        """
        try:
            result = await self.supabase.table("generation_tasks").select("params").eq(
                "task_id", task_id,
            ).eq("user_id", user_id).single().execute()

            if result.data:
                return result.data.get("params", {})

            return None

        except Exception as e:
            logger.warning(f"Failed to get task params: {e}")
            return None
