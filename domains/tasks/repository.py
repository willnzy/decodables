"""Tasks Repository - Data access interface.

@module domains.tasks.repository
@version 1.0.0
"""

from typing import Protocol, Optional, Dict, Any


class TasksRepository(Protocol):
    """Repository interface for background tasks operations."""

    async def get_task_from_database(
        self,
        task_id: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get task details from database (fallback when not in cache).

        Args:
            task_id: Task identifier
            user_id: User ID (for ownership verification)

        Returns:
            Task details dict or None if not found
        """
        ...

    async def get_task_params(
        self,
        task_id: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get task parameters (for credit refund lookup).

        Args:
            task_id: Task identifier
            user_id: User ID (for ownership verification)

        Returns:
            Task params dict or None if not found
        """
        ...
