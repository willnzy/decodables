"""Subscription Pause Service (SVC-008 Phase 5+).

Handles subscription pause/resume lifecycle with configurable max duration.
Implements BR-007: pause max 30 days, auto-resume after expiry.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SubscriptionPauseService:
    """Manages subscription pause/resume operations.

    Responsibilities:
    1. Pause an active subscription for up to MAX_PAUSE_DAYS
    2. Resume a paused subscription
    3. Track pause status (reason, resume_at timestamp)
    4. Find expired pauses for auto-resume scheduler
    """

    MAX_PAUSE_DAYS = 30  # Maximum pause duration per BR-007

    def __init__(self, db_client=None):
        """Initialize with optional database client.

        Args:
            db_client: Database client for supabase queries
        """
        self._db = db_client

    async def pause_subscription(
        self, user_id: str, reason: str = "", duration_days: int = 30
    ) -> Dict[str, Any]:
        """Pause a user's subscription for up to MAX_PAUSE_DAYS.

        Args:
            user_id: The user's ID
            reason: Optional reason for pause
            duration_days: Requested pause duration (clamped to MAX_PAUSE_DAYS)

        Returns:
            Dictionary with pause status and resume timestamp
        """
        duration = min(duration_days, self.MAX_PAUSE_DAYS)
        resume_at = datetime.now(timezone.utc) + timedelta(days=duration)

        logger.info(
            "pause_subscription",
            extra={
                "event": "subscription.pause",
                "user_id": user_id,
                "duration_days": duration,
                "resume_at": resume_at.isoformat(),
                "reason": reason,
            },
        )

        if self._db:
            await self._db.table("profiles").update({
                "subscription_status": "paused",
                "pause_reason": reason if reason else None,
                "pause_resume_at": resume_at.isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", user_id).execute()

        return {
            "user_id": user_id,
            "status": "paused",
            "resume_at": resume_at.isoformat(),
            "duration_days": duration,
        }

    async def resume_subscription(self, user_id: str) -> Dict[str, Any]:
        """Resume a paused subscription.

        Args:
            user_id: The user's ID

        Returns:
            Dictionary with active status
        """
        logger.info(
            "resume_subscription",
            extra={
                "event": "subscription.resume",
                "user_id": user_id,
            },
        )

        if self._db:
            await self._db.table("profiles").update({
                "subscription_status": "active",
                "pause_reason": None,
                "pause_resume_at": None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", user_id).execute()

        return {"user_id": user_id, "status": "active"}

    async def get_pause_status(
        self, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get current pause status for a user.

        Args:
            user_id: The user's ID

        Returns:
            Pause status dict or None if not paused
        """
        if not self._db:
            return None

        try:
            result = await self._db.table("profiles").select(
                "subscription_status, pause_reason, pause_resume_at"
            ).eq("id", user_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            logger.warning(
                "get_pause_status failed",
                extra={"event": "subscription.pause_status_error", "error": str(e)},
            )
            return None

    async def get_expired_pauses(self) -> list:
        """Find all users whose pause has expired.

        Used for auto-resume scheduler to identify pauses that need resumption.

        Returns:
            List of user records with expired pauses
        """
        if not self._db:
            return []

        try:
            now = datetime.now(timezone.utc).isoformat()
            result = await self._db.table("profiles").select(
                "id, email, tier"
            ).eq("subscription_status", "paused").lt(
                "pause_resume_at", now
            ).execute()
            return result.data or []
        except Exception as e:
            logger.warning(
                "get_expired_pauses failed",
                extra={"event": "subscription.expired_pauses_error", "error": str(e)},
            )
            return []
