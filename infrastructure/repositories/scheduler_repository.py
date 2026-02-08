"""
Scheduler Repository Implementation (REPO-008 Phase 5+)

@module infrastructure.repositories.scheduler_repository
@version 1.0.0

Provides data access for scheduler state management using Supabase.
Uses the system_configs table with keys like 'scheduler.{task_name}.last_run'
for storing scheduler execution state and lock information.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from core.database import retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseSchedulerRepository:
    """Supabase implementation of scheduler state repository."""

    def __init__(self, client):
        """
        Initialize repository with AsyncClient.

        Args:
            client: AsyncClient instance
        """
        self.client = client

    def _get_lock_key(self, task_name: str) -> str:
        """Get the lock key for a task in system_configs."""
        return f"scheduler.{task_name}.lock"

    def _get_last_run_key(self, task_name: str) -> str:
        """Get the last_run key for a task in system_configs."""
        return f"scheduler.{task_name}.last_run"

    def _get_last_status_key(self, task_name: str) -> str:
        """Get the last status key for a task in system_configs."""
        return f"scheduler.{task_name}.last_status"

    @retry_on_network_error()
    async def acquire_lock(self, task_name: str, ttl_seconds: int = 3600) -> bool:
        """
        Acquire a lock to prevent concurrent execution of a task.

        Uses system_configs table with key 'scheduler.{task_name}.lock'.
        Lock expires after ttl_seconds.

        Args:
            task_name: Name of the scheduler task
            ttl_seconds: Lock time-to-live in seconds

        Returns:
            True if lock acquired, False if already locked
        """
        try:
            lock_key = self._get_lock_key(task_name)
            now = datetime.now(timezone.utc).isoformat()

            # Check if lock exists and is not expired
            result = await self.client.table("system_configs").select("*").eq(
                "key", lock_key
            ).single().execute()

            if result.data:
                lock_data = result.data.get("value", {})
                locked_at = lock_data.get("locked_at")

                if locked_at:
                    try:
                        locked_dt = datetime.fromisoformat(locked_at.replace("Z", "+00:00"))
                        age_seconds = (datetime.now(timezone.utc) - locked_dt).total_seconds()

                        # If lock is still fresh, reject acquisition
                        if age_seconds < ttl_seconds:
                            logger.warning(f"[Scheduler] Lock already held for task '{task_name}'")
                            return False
                    except ValueError:
                        pass

            # Acquire or update lock
            await self.client.table("system_configs").upsert({
                "key": lock_key,
                "value": {
                    "locked_at": now,
                    "locked_by": "scheduler",
                    "ttl_seconds": ttl_seconds
                }
            }).execute()

            logger.info(f"[Scheduler] Lock acquired for task '{task_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to acquire lock for task {task_name}: {e}")
            return False

    @retry_on_network_error()
    async def release_lock(self, task_name: str) -> bool:
        """
        Release the lock for a task.

        Args:
            task_name: Name of the scheduler task

        Returns:
            True if lock released, False on error
        """
        try:
            lock_key = self._get_lock_key(task_name)

            await self.client.table("system_configs").delete().eq(
                "key", lock_key
            ).execute()

            logger.info(f"[Scheduler] Lock released for task '{task_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to release lock for task {task_name}: {e}")
            return False

    @retry_on_network_error()
    async def get_last_run(self, task_name: str) -> Optional[datetime]:
        """
        Get the last execution timestamp for a task.

        Args:
            task_name: Name of the scheduler task

        Returns:
            datetime of last run or None if never run
        """
        try:
            last_run_key = self._get_last_run_key(task_name)

            result = await self.client.table("system_configs").select("*").eq(
                "key", last_run_key
            ).single().execute()

            if result.data:
                last_run_data = result.data.get("value", {})
                last_run_str = last_run_data.get("timestamp")

                if last_run_str:
                    try:
                        return datetime.fromisoformat(last_run_str.replace("Z", "+00:00"))
                    except ValueError:
                        logger.warning(f"Invalid last_run timestamp for {task_name}: {last_run_str}")

            return None

        except Exception as e:
            logger.error(f"Failed to get last_run for task {task_name}: {e}")
            return None

    @retry_on_network_error()
    async def record_run(
        self,
        task_name: str,
        status: str,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Record a task execution (start, success, failure).

        Stores in system_configs with keys:
        - scheduler.{task_name}.last_run → {timestamp, duration_ms, status}
        - scheduler.{task_name}.last_status → {status, timestamp, details}

        Args:
            task_name: Name of the scheduler task
            status: Execution status (running, success, failed, timeout, etc)
            details: Optional execution details (error message, items processed, etc)

        Returns:
            True if recorded, False on error
        """
        try:
            now = datetime.now(timezone.utc)
            now_iso = now.isoformat()

            # Update last_run record
            last_run_key = self._get_last_run_key(task_name)
            last_run_value = {
                "timestamp": now_iso,
                "status": status,
                "details": details or {}
            }

            await self.client.table("system_configs").upsert({
                "key": last_run_key,
                "value": last_run_value
            }).execute()

            # Update last_status record
            last_status_key = self._get_last_status_key(task_name)
            last_status_value = {
                "status": status,
                "timestamp": now_iso,
                "details": details or {}
            }

            await self.client.table("system_configs").upsert({
                "key": last_status_key,
                "value": last_status_value
            }).execute()

            logger.info(f"[Scheduler] Recorded run for '{task_name}': {status}")
            return True

        except Exception as e:
            logger.error(f"Failed to record run for task {task_name}: {e}")
            return False

    @retry_on_network_error()
    async def get_task_status(self, task_name: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a scheduler task.

        Args:
            task_name: Name of the scheduler task

        Returns:
            Dict with status, timestamp, details or None
        """
        try:
            last_status_key = self._get_last_status_key(task_name)

            result = await self.client.table("system_configs").select("*").eq(
                "key", last_status_key
            ).single().execute()

            if result.data:
                return result.data.get("value", {})

            return None

        except Exception as e:
            logger.error(f"Failed to get status for task {task_name}: {e}")
            return None

    @retry_on_network_error()
    async def get_all_task_statuses(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all scheduler tasks.

        Returns:
            Dict mapping task_name → status data
        """
        try:
            result = await self.client.table("system_configs").select("*").like(
                "key", "scheduler.%.last_status"
            ).execute()

            statuses = {}
            for config in result.data or []:
                key = config.get("key", "")
                # Extract task name from key: "scheduler.{task_name}.last_status"
                parts = key.split(".")
                if len(parts) >= 3:
                    task_name = ".".join(parts[1:-1])  # Handle task names with dots
                    statuses[task_name] = config.get("value", {})

            return statuses

        except Exception as e:
            logger.error(f"Failed to get all task statuses: {e}")
            return {}

    @retry_on_network_error()
    async def clear_old_locks(self, older_than_seconds: int = 7200) -> int:
        """
        Clear expired locks (older than specified seconds).

        Useful for cleanup when a scheduler task crashes and leaves a stale lock.

        Args:
            older_than_seconds: Delete locks older than this many seconds

        Returns:
            Number of locks cleared
        """
        try:
            cutoff = datetime.now(timezone.utc)
            from datetime import timedelta
            cutoff = (cutoff - timedelta(seconds=older_than_seconds)).isoformat()

            # Find all locks
            result = await self.client.table("system_configs").select("*").like(
                "key", "scheduler.%.lock"
            ).execute()

            cleared_count = 0
            for config in result.data or []:
                value = config.get("value", {})
                locked_at = value.get("locked_at")

                if locked_at:
                    try:
                        locked_dt = datetime.fromisoformat(locked_at.replace("Z", "+00:00"))
                        if locked_dt.isoformat() < cutoff:
                            await self.client.table("system_configs").delete().eq(
                                "id", config.get("id")
                            ).execute()
                            cleared_count += 1
                    except ValueError:
                        pass

            logger.info(f"[Scheduler] Cleared {cleared_count} expired locks")
            return cleared_count

        except Exception as e:
            logger.error(f"Failed to clear old locks: {e}")
            return 0
