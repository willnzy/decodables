"""
Admin Tasks Service - Background task management operations.

@module domains.admin.admin_tasks_service
@version 1.0.0

This service encapsulates admin-specific task management operations:
- Task status querying
- Task logs querying
- Task health monitoring
- Manual task triggering

Architecture: API → Container → Service → Repository
"""

import logging
from typing import Dict, List, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# =============================================================================
# Repository Protocol (DIP compliance)
# =============================================================================

@runtime_checkable
class TasksRepositoryProtocol(Protocol):
    """Protocol for tasks repository operations."""
    async def get_task_status(self) -> List[Dict]: ...
    async def get_task_logs(
        self,
        task_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]: ...
    async def get_tasks_health(self) -> Dict: ...


# =============================================================================
# Constants
# =============================================================================

# Valid task statuses
VALID_TASK_STATUSES = {"success", "failed", "running", "pending"}

# Valid task names
VALID_TASK_NAMES = {"hourly", "daily", "all", "cleanup", "retention"}


class AdminTasksService:
    """
    Admin Tasks Service.

    Handles all admin-specific task management operations.
    Provides unified interface for task monitoring and control.
    """

    def __init__(self, tasks_repo: TasksRepositoryProtocol):
        """
        Initialize Admin Tasks Service with repository dependency.

        WHY interface injection?
        - Dependency Inversion Principle (DIP)
        - Easy mocking for tests
        - Decouples from infrastructure

        Args:
            tasks_repo: Tasks repository
        """
        self._tasks_repo = tasks_repo

    # =========================================================================
    # Task Status
    # =========================================================================

    async def get_task_status(self) -> Dict:
        """
        Get status of all scheduled tasks.

        Returns:
            Dict with tasks list
        """
        task_status = await self._tasks_repo.get_task_status()
        return {"tasks": task_status}

    # =========================================================================
    # Task Logs
    # =========================================================================

    async def get_task_logs(
        self,
        task_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> Dict:
        """
        Get task execution logs.

        Args:
            task_name: Filter by task name
            status: Filter by status
            limit: Maximum results

        Returns:
            Dict with logs list

        Raises:
            ValueError: If status or task_name is invalid
        """
        # Validate status
        if status is not None and status not in VALID_TASK_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(VALID_TASK_STATUSES)}")

        # Validate task_name
        if task_name is not None and task_name not in VALID_TASK_NAMES:
            raise ValueError(f"Invalid task_name. Must be one of: {', '.join(VALID_TASK_NAMES)}")

        logs = await self._tasks_repo.get_task_logs(task_name, status, limit)
        return {"logs": logs}

    # =========================================================================
    # Task Health
    # =========================================================================

    async def get_tasks_health(self) -> Dict:
        """
        Get overall task health status.

        Returns:
            Dict with status, scheduler, last_hour metrics
        """
        health_metrics = await self._tasks_repo.get_tasks_health()

        # Check scheduler status
        scheduler_status = "unknown"
        try:
            from scheduler import scheduler
            if scheduler and scheduler.running:
                scheduler_status = "running"
            else:
                scheduler_status = "stopped"
        except Exception:
            pass

        # Determine overall health status
        failed_runs = health_metrics.get("failed_runs", 0)
        status = "healthy" if failed_runs == 0 else "degraded"

        return {
            "status": status,
            "scheduler": scheduler_status,
            "last_hour": {
                "total_runs": health_metrics.get("total_runs", 0),
                "failed_runs": failed_runs,
                "success_rate": health_metrics.get("success_rate", 0.0)
            }
        }

    # =========================================================================
    # Task Execution
    # =========================================================================

    def run_task(self, task_name: str) -> Dict:
        """
        Manually trigger a scheduled task.

        Args:
            task_name: Task to run (hourly, daily, all, cleanup, retention)

        Returns:
            Dict with status, task, result

        Raises:
            ValueError: If task_name is invalid
        """
        if task_name not in VALID_TASK_NAMES:
            raise ValueError(f"Invalid task. Valid tasks: {', '.join(VALID_TASK_NAMES)}")

        if task_name == "cleanup":
            from scheduler import run_storage_cleanup
            run_storage_cleanup()
            result = {"status": "completed", "task_type": "cleanup"}
        elif task_name == "retention":
            from scheduler import run_aggregation_now
            result = run_aggregation_now("daily")
            result["task_type"] = "retention"
        else:
            from scheduler import run_aggregation_now
            result = run_aggregation_now(task_name)

        return {"status": "triggered", "task": task_name, "result": result}
