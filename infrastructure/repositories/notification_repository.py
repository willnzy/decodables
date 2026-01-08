"""
Notification Repository - Notification management operations.

@module infrastructure.repositories.notification_repository
@version 1.0.0

Provides notification CRUD operations.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from core.database import get_supabase_client, retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseNotificationRepository:
    """
    Notification repository for notifications table operations.
    """

    def __init__(self, client=None):
        """Initialize repository with database client."""
        self._client = client

    @property
    def client(self):
        """Lazy load Supabase client."""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    @retry_on_network_error()
    async def create_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: str = "info",
        action_url: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new notification."""
        result = self.client.table("notifications").insert({
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": notification_type,
            "action_url": action_url,
            "is_read": False,
        }).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get user notifications."""
        query = self.client.table("notifications").select("*").eq(
            "user_id", user_id
        )

        if unread_only:
            query = query.eq("is_read", False)

        result = query.order("created_at", desc=True).limit(limit).execute()
        return result.data or []

    @retry_on_network_error()
    async def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """Mark notification as read."""
        result = self.client.table("notifications").update({
            "is_read": True
        }).eq("id", notification_id).eq("user_id", user_id).execute()

        return len(result.data) > 0 if result.data else False

    @retry_on_network_error()
    async def mark_all_as_read(self, user_id: str) -> bool:
        """Mark all notifications as read."""
        result = self.client.table("notifications").update({
            "is_read": True
        }).eq("user_id", user_id).eq("is_read", False).execute()

        return True

    @retry_on_network_error()
    async def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """Delete a notification."""
        result = self.client.table("notifications").delete().eq(
            "id", notification_id
        ).eq("user_id", user_id).execute()

        return len(result.data) > 0 if result.data else False

    # ==========================================
    # Admin Methods
    # ==========================================

    @retry_on_network_error()
    async def create_broadcast(
        self,
        title: str,
        content: str,
        target_group: str = "all"
    ) -> Dict[str, Any]:
        """
        Create a broadcast notification for a group of users.

        Args:
            title: Notification title
            content: Notification content
            target_group: Target user group ('all', 'free', 'starter', 'pro')

        Returns:
            Broadcast information
        """
        # Get target users based on group
        if target_group == "all":
            users_result = self.client.table("profiles").select("id").execute()
        else:
            users_result = self.client.table("profiles").select("id").eq(
                "tier", target_group
            ).execute()

        users = users_result.data or []
        user_ids = [u["id"] for u in users]

        # Create notifications for all users
        notifications = []
        for user_id in user_ids:
            notification = await self.create_notification(
                user_id=user_id,
                title=title,
                message=content,
                notification_type="system"
            )
            if notification:
                notifications.append(notification)

        return {
            "target_group": target_group,
            "user_count": len(user_ids),
            "notification_count": len(notifications),
            "title": title
        }

    @retry_on_network_error()
    async def send_notification_to_user(
        self,
        user_id: str,
        title: str,
        content: str,
        notification_type: str = "system"
    ) -> Optional[Dict[str, Any]]:
        """Send a notification to a single user."""
        return await self.create_notification(
            user_id=user_id,
            title=title,
            message=content,
            notification_type=notification_type
        )

    @retry_on_network_error()
    async def send_notification_to_users(
        self,
        user_ids: List[str],
        title: str,
        content: str,
        notification_type: str = "system"
    ) -> List[Dict[str, Any]]:
        """Send notifications to multiple users."""
        notifications = []
        for user_id in user_ids:
            notification = await self.create_notification(
                user_id=user_id,
                title=title,
                message=content,
                notification_type=notification_type
            )
            if notification:
                notifications.append(notification)
        return notifications

    @retry_on_network_error()
    async def get_all_notification_stats(self) -> Dict[str, Any]:
        """Get overall notification statistics."""
        # Total notifications
        total_result = self.client.table("notifications").select(
            "id", count="exact"
        ).execute()

        # Unread notifications
        unread_result = self.client.table("notifications").select(
            "id", count="exact"
        ).eq("is_read", False).execute()

        # Notifications by type
        by_type_result = self.client.table("notifications").select(
            "type"
        ).execute()

        by_type = {}
        for n in (by_type_result.data or []):
            ntype = n.get("type", "unknown")
            by_type[ntype] = by_type.get(ntype, 0) + 1

        return {
            "total": total_result.count or 0,
            "unread": unread_result.count or 0,
            "read": (total_result.count or 0) - (unread_result.count or 0),
            "by_type": by_type
        }

    @retry_on_network_error()
    async def get_notification_history(
        self,
        offset: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get paginated notification history using offset pagination."""
        result = self.client.table("notifications").select(
            "*, profiles(email, username)", count="exact"
        ).order("created_at", desc=True).range(
            offset, offset + limit - 1
        ).execute()

        return {
            "items": result.data or [],
            "total": result.count or 0,
            "offset": offset,
            "limit": limit
        }
