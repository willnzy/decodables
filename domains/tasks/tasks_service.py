"""Tasks Service - Business logic for user background tasks.

@module domains.tasks.tasks_service
@version 1.1.0 (DDD Error Handling)

Changes:
- v1.1.0: DDD-compliant error handling
  - Replaced HTTPException with domain-specific exceptions
  - API layer should catch and convert to HTTP responses
- v1.0.0: Initial implementation
"""

import logging
import re
from typing import Optional, Dict, Any, TYPE_CHECKING

from infrastructure.task_queue import task_queue, progress_tracker

if TYPE_CHECKING:
    from domains.billing import BillingService

logger = logging.getLogger(__name__)


# ==========================================
# Domain Exceptions (DDD-compliant)
# ==========================================

class TaskException(Exception):
    """Base exception for task-related errors."""
    pass


class InvalidTaskIdException(TaskException):
    """Raised when task ID format is invalid."""
    pass


class TaskNotFoundException(TaskException):
    """Raised when task is not found."""
    pass


class TaskNotCancellableException(TaskException):
    """Raised when task cannot be cancelled."""
    def __init__(self, current_status: str):
        self.current_status = current_status
        super().__init__(f"Cannot cancel task in '{current_status}' status")


class TaskCancellationFailedException(TaskException):
    """Raised when task cancellation fails."""
    pass


# ==========================================
# Constants
# ==========================================

# Task ID format validation (3-64 chars, alphanumeric/hyphen/underscore)
TASK_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,64}$")

# WS-14: All valid task states (complete definition)
VALID_TASK_STATUSES = (
    "pending", "queued", "scheduled",
    "processing", "completed", "failed", "cancelled"
)

# Terminal states (no further transitions allowed)
TERMINAL_STATUSES = ("completed", "failed", "cancelled")

# Cancellable task statuses (including scheduled from RQ)
CANCELLABLE_STATUSES = ("pending", "queued", "scheduled")


class TasksService:
    """Service for user background tasks business logic."""

    def __init__(self, repository, billing_service: "BillingService"):
        """
        Initialize with repository and billing service.

        Args:
            repository: User tasks repository (SupabaseUserTasksRepository)
            billing_service: BillingService for credit refund operations
        """
        self.repository = repository
        self._billing_service = billing_service

    # ==========================================
    # Validation
    # ==========================================

    def validate_task_id(self, task_id: str) -> None:
        """
        Validate task_id format.

        Args:
            task_id: Task identifier to validate

        Raises:
            InvalidTaskIdException: If task_id format is invalid
        """
        if not TASK_ID_PATTERN.match(task_id):
            raise InvalidTaskIdException("Invalid task ID format")

    # ==========================================
    # Query Operations
    # ==========================================

    async def get_task_status(
        self,
        task_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Get task status and progress.

        Business logic:
        1. Validate task_id format
        2. Try to get status from Redis cache (primary)
        3. Fallback to database if not in cache
        4. Return task status details

        Args:
            task_id: Task identifier
            user_id: User ID (for ownership verification)

        Returns:
            Task status dict with:
            - status: pending, queued, processing, completed, failed, cancelled
            - progress: 0-100
            - current_step/total_steps: for progress bar
            - result: image URLs when completed
            - error: error message if failed

        Raises:
            InvalidTaskIdException: If task_id format is invalid
            TaskNotFoundException: If task not found
        """
        # Validate format
        self.validate_task_id(task_id)

        # Try Redis cache first (primary data source)
        status = progress_tracker.get_status(task_id)

        if status:
            return {
                "task_id": task_id,
                "status": status.get("status", "unknown"),
                "progress": status.get("progress", 0),
                "current_step": status.get("current_step"),
                "total_steps": status.get("total_steps"),
                "message": status.get("message"),
                "result": status.get("result"),
                "error": status.get("error"),
                "created_at": status.get("created_at"),
                "completed_at": status.get("completed_at"),
            }

        # Fallback to database
        db_data = await self.repository.get_task_from_database(task_id, user_id)

        if db_data:
            return {
                "task_id": task_id,
                "status": db_data.get("status", "unknown"),
                "progress": db_data.get("progress", 0),
                "current_step": db_data.get("current_step"),
                "total_steps": db_data.get("total_steps"),
                "message": db_data.get("message"),
                "result": db_data.get("result"),
                "error": db_data.get("error"),
                "created_at": db_data.get("created_at"),
                "completed_at": db_data.get("completed_at"),
            }

        # Task not found in cache or database
        raise TaskNotFoundException("Task not found")

    # ==========================================
    # Command Operations
    # ==========================================

    async def cancel_task(
        self,
        task_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Cancel a pending or queued task.

        Business logic:
        1. Validate task_id format
        2. Check task exists and get current status
        3. Verify task is cancellable (pending/queued/scheduled only)
        4. Attempt cancellation via task queue
        5. Refund credits if task had charges
        6. Return cancellation result

        Args:
            task_id: Task identifier
            user_id: User ID (for ownership verification)

        Returns:
            Dict with:
            - status: "cancelled"
            - task_id: Task identifier
            - credits_refunded: Amount refunded (0 if none)
            - message: Success message

        Raises:
            InvalidTaskIdException: If task_id format is invalid
            TaskNotFoundException: If task not found
            TaskNotCancellableException: If task status doesn't allow cancellation
            TaskCancellationFailedException: If cancellation operation fails
        """
        # Validate format
        self.validate_task_id(task_id)

        # WS-14: Check task status from Redis first, fallback to DB
        status = progress_tracker.get_status(task_id)

        if not status:
            # Fallback to DB if Redis doesn't have the status
            db_data = await self.repository.get_task_from_database(task_id, user_id)
            if not db_data:
                raise TaskNotFoundException("Task not found")
            status = db_data

        # Verify task is cancellable
        current_status = status.get("status")
        if current_status not in CANCELLABLE_STATUSES:
            raise TaskNotCancellableException(current_status)

        # Attempt cancellation
        if not task_queue.cancel_task(task_id, user_id):
            raise TaskCancellationFailedException("Failed to cancel task")

        # Handle credit refund
        credits_refunded = await self._refund_task_credits(task_id, user_id)

        return {
            "status": "cancelled",
            "task_id": task_id,
            "credits_refunded": credits_refunded,
            "message": "Task cancelled" + (" and credits refunded" if credits_refunded else ""),
        }

    # ==========================================
    # Helper Methods
    # ==========================================

    async def _refund_task_credits(
        self,
        task_id: str,
        user_id: str,
    ) -> int:
        """
        Refund credits for cancelled task.

        Args:
            task_id: Task identifier
            user_id: User ID

        Returns:
            Amount of credits refunded (0 if none)
        """
        try:
            # Get task params to check if credits were charged
            params = await self.repository.get_task_params(task_id, user_id)

            if not params:
                return 0

            credits_charged = params.get("credits_charged", 0)

            if credits_charged <= 0:
                return 0

            # WS-01 fix: Use BillingService for atomic refund (replaces legacy credit_repository.add_credits)
            from domains.billing import TransactionType, CreditBucket
            await self._billing_service.add_credits(
                user_id=user_id,
                amount=credits_charged,
                bucket=CreditBucket.PERMANENT,
                tx_type=TransactionType.REFUND,
                description=f"Cancelled task {task_id}",
                idempotency_key=f"task_refund_{task_id}_{user_id}",
            )

            return credits_charged

        except Exception as e:
            logger.warning(f"Failed to refund credits for cancelled task: {e}")
            return 0
