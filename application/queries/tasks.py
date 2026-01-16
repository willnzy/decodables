"""Tasks Queries - Read operations for user background tasks.

@module application.queries.tasks
@version 1.1.0 (DDD Error Handling)

Changes:
- v1.1.0: DDD-compliant error handling
  - Catch domain exceptions and convert to HTTPException
  - Architecture: API → Handler → Service (exceptions bubble up as HTTP)
- v1.0.0: Initial implementation
"""

from dataclasses import dataclass
from typing import Dict, Any

from fastapi import HTTPException

from domains.tasks.tasks_service import (
    InvalidTaskIdException,
    TaskNotFoundException,
    TaskNotCancellableException,
    TaskCancellationFailedException,
)


# ==========================================
# Get Task Status Query
# ==========================================

@dataclass
class GetTaskStatusQuery:
    """Query to get task status and progress."""
    task_id: str
    user_id: str


@dataclass
class GetTaskStatusResult:
    """Result of task status query."""
    task_data: Dict[str, Any]


class GetTaskStatusHandler:
    """Handler for GetTaskStatusQuery."""

    def __init__(self, tasks_service):
        """
        Initialize with TasksService.

        Args:
            tasks_service: TasksService instance
        """
        self._tasks_service = tasks_service

    async def handle(self, query: GetTaskStatusQuery) -> GetTaskStatusResult:
        """
        Execute query to get task status.

        Args:
            query: GetTaskStatusQuery

        Returns:
            GetTaskStatusResult with task status data

        Raises:
            HTTPException: Converted from domain exceptions
        """
        try:
            task_data = await self._tasks_service.get_task_status(
                query.task_id,
                query.user_id,
            )
            return GetTaskStatusResult(task_data=task_data)
        except InvalidTaskIdException as e:
            raise HTTPException(400, str(e))
        except TaskNotFoundException as e:
            raise HTTPException(404, str(e))


# ==========================================
# Cancel Task Command
# ==========================================

@dataclass
class CancelTaskCommand:
    """Command to cancel a task."""
    task_id: str
    user_id: str


@dataclass
class CancelTaskResult:
    """Result of task cancellation."""
    result_data: Dict[str, Any]


class CancelTaskHandler:
    """Handler for CancelTaskCommand."""

    def __init__(self, tasks_service):
        """
        Initialize with TasksService.

        Args:
            tasks_service: TasksService instance
        """
        self._tasks_service = tasks_service

    async def handle(self, command: CancelTaskCommand) -> CancelTaskResult:
        """
        Execute command to cancel task.

        Args:
            command: CancelTaskCommand

        Returns:
            CancelTaskResult with cancellation result

        Raises:
            HTTPException: Converted from domain exceptions
        """
        try:
            result_data = await self._tasks_service.cancel_task(
                command.task_id,
                command.user_id,
            )
            return CancelTaskResult(result_data=result_data)
        except InvalidTaskIdException as e:
            raise HTTPException(400, str(e))
        except TaskNotFoundException as e:
            raise HTTPException(404, str(e))
        except TaskNotCancellableException as e:
            raise HTTPException(400, str(e))
        except TaskCancellationFailedException as e:
            raise HTTPException(400, str(e))
