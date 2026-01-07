"""
Notification Repository Extended - Additional methods for services/db migration.

@module infrastructure.repositories.notification_repository_extended
@version 1.0.0

Provides all notification operations needed to replace services/db/notifications.py.
"""

import logging
from typing import Optional, Dict, Any, List

from core.database import retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseNotificationRepositoryExtended:
    """
    Extended notification repository for notifications table operations.

    Provides all methods needed to replace services/db/notifications.py functions.
    """

    def __init__(self, client):
        """
        Initialize repository with database client.

        Args:
            client: Supabase database client
        """
        self.client = client

    @retry_on_network_error()
    async def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get user notifications.

        Args:
            user_id: User ID
            unread_only: Only get unread notifications
            limit: Maximum number of notifications

        Returns:
            List of notification dicts
        """
        query = self.client.table("notifications").select("*").eq("user_id", user_id)

        if unread_only:
            query = query.eq("is_read", False)

        result = query.order("created_at", desc=True).limit(limit).execute()
        return result.data or []

    @retry_on_network_error()
    async def mark_notification_read(
        self,
        notification_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Mark notification as read.

        Args:
            notification_id: Notification ID
            user_id: User ID (for ownership check)

        Returns:
            Updated notification dict
        """
        result = self.client.table("notifications").update({"is_read": True}).eq(
            "id", notification_id
        ).eq("user_id", user_id).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def mark_all_notifications_read(
        self,
        user_id: str
    ) -> bool:
        """
        Mark all notifications as read.

        Args:
            user_id: User ID

        Returns:
            True if successful
        """
        self.client.table("notifications").update({"is_read": True}).eq(
            "user_id", user_id
        ).execute()
        return True

    @retry_on_network_error()
    async def create_broadcast(
        self,
        title: str,
        content: str,
        target_group: str = "all"
    ) -> Optional[Dict[str, Any]]:
        """
        Create broadcast notification.

        Args:
            title: Broadcast title
            content: Broadcast content
            target_group: Target group (all, free, starter, pro)

        Returns:
            Created broadcast dict
        """
        result = self.client.table("broadcasts").insert({
            "title": title,
            "content": content,
            "target_group": target_group,
        }).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def send_notification_to_user(
        self,
        user_id: str,
        title: str,
        content: str,
        notification_type: str = "system"
    ) -> Optional[Dict[str, Any]]:
        """
        Send notification to single user.

        Args:
            user_id: User ID
            title: Notification title
            content: Notification content
            notification_type: Notification type (system, marketplace, etc.)

        Returns:
            Created notification dict
        """
        result = self.client.table("notifications").insert({
            "user_id": user_id,
            "title": title,
            "content": content,
            "type": notification_type,
        }).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def send_notification_to_users(
        self,
        user_ids: List[str],
        title: str,
        content: str,
        notification_type: str = "system"
    ) -> List[Dict[str, Any]]:
        """
        Send notification to multiple users.

        Args:
            user_ids: List of user IDs
            title: Notification title
            content: Notification content
            notification_type: Notification type

        Returns:
            List of created notification dicts
        """
        if not user_ids:
            return []

        records = [
            {
                "user_id": uid,
                "title": title,
                "content": content,
                "type": notification_type,
            }
            for uid in user_ids
        ]

        result = self.client.table("notifications").insert(records).execute()
        return result.data or []

    @retry_on_network_error()
    async def get_all_notification_stats(self) -> Dict[str, Any]:
        """
        Get notification statistics.

        Returns:
            Dict with total and unread counts
        """
        total = self.client.table("notifications").select("id", count="exact").execute()
        unread = self.client.table("notifications").select("id", count="exact").eq(
            "is_read", False
        ).execute()

        return {
            "total": total.count or 0,
            "unread": unread.count or 0,
        }

    @retry_on_network_error()
    async def get_notification_history(
        self,
        page: int = 1,
        limit: int = 50,
        notification_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get notification history (admin function).

        Args:
            page: Page number
            limit: Items per page
            notification_type: Optional filter by type

        Returns:
            List of notification dicts
        """
        offset = (page - 1) * limit
        query = self.client.table("notifications").select("*")

        if notification_type:
            query = query.eq("type", notification_type)

        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return result.data or []
