"""
Activity Log Repository - Data access layer for activity logging.

Centralizes all activity_logs table operations. Webhook services and other
callers should use this repository instead of direct table("activity_logs") inserts.

@module infrastructure.repositories.activity_log_repository
@version 1.0.0

Created in WS2 (payment system audit) to consolidate 9+ scattered
table("activity_logs").insert(...) calls into a single repository.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ActivityLogRepository:
    """
    Repository for activity_logs table operations.

    All activity logging should go through this repository to ensure
    consistent field names and error handling.
    """

    def __init__(self, db_client):
        """
        Initialize with database client.

        Args:
            db_client: Supabase async client instance
        """
        self.client = db_client

    async def log_activity(
        self,
        user_id: str,
        action: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log a user activity event.

        This is a non-critical operation — failures are logged as warnings
        and do not propagate exceptions.

        Args:
            user_id: User ID performing the action
            action: Action type (e.g. 'user_signup', 'credits_purchase',
                    'subscription_start', 'subscription_cancel', etc.)
            metadata: Optional dict with additional context
        """
        try:
            await self.client.table("activity_logs").insert({
                "user_id": user_id,
                "action": action,
                "metadata": metadata or {},
            }).execute()
        except Exception as e:
            logger.warning(f"[ActivityLogRepo] Failed to log activity '{action}' for {user_id}: {e}")
