"""
Notification Template Repository - Admin notification template CRUD operations.

@module infrastructure.repositories.notification_template_repository
@version 1.0.0

Provides CRUD operations for admin_notification_templates table.
Supports draft, scheduled, and sent notification workflow.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import json

from core.database import retry_on_network_error
from domains.platform.repository import INotificationTemplateRepository

logger = logging.getLogger(__name__)


class SupabaseNotificationTemplateRepository(INotificationTemplateRepository):
    """
    Repository for admin_notification_templates table operations.

    v1.0.0: Initial implementation for Admin Panel CRUD.
    """

    TABLE_NAME = "admin_notification_templates"

    def __init__(self, client):
        """
        Initialize repository with AsyncClient.

        Args:
            client: AsyncClient instance (required)

        Raises:
            ValueError: If client is None
        """
        if client is None:
            raise ValueError("AsyncClient required for SupabaseNotificationTemplateRepository")
        self._client = client

    @property
    def client(self):
        """Get AsyncClient instance."""
        return self._client

    @retry_on_network_error()
    async def create(
        self,
        title: str,
        message: str,
        notification_type: str,
        channel: str,
        target_users: Optional[List[str]],
        target_tiers: Optional[List[str]],
        scheduled_at: Optional[str],
        created_by: str
    ) -> Dict[str, Any]:
        """Create a new notification template."""
        status = "scheduled" if scheduled_at else "draft"

        data = {
            "title": title,
            "message": message,
            "notification_type": notification_type,
            "channel": channel,
            "status": status,
            "target_users": target_users,
            "target_tiers": target_tiers,
            "scheduled_at": scheduled_at,
            "created_by": created_by,
        }

        result = await self.client.table(self.TABLE_NAME).insert(data).execute()

        if not result.data:
            raise Exception("Failed to create notification template")

        return self._transform_row(result.data[0])

    @retry_on_network_error()
    async def get_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get notification template by ID."""
        result = await self.client.table(self.TABLE_NAME).select("*").eq(
            "id", template_id
        ).execute()

        if not result.data:
            return None

        return self._transform_row(result.data[0])

    @retry_on_network_error()
    async def get_list(
        self,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get paginated list of notification templates."""
        query = self.client.table(self.TABLE_NAME).select("*", count="exact")

        if status:
            query = query.eq("status", status)

        result = await query.order(
            "created_at", desc=True
        ).range(offset, offset + limit - 1).execute()

        notifications = [self._transform_row(row) for row in (result.data or [])]

        return {
            "notifications": notifications,
            "total": result.count or 0,
        }

    @retry_on_network_error()
    async def update(
        self,
        template_id: str,
        title: Optional[str] = None,
        message: Optional[str] = None,
        notification_type: Optional[str] = None,
        channel: Optional[str] = None,
        target_users: Optional[List[str]] = None,
        target_tiers: Optional[List[str]] = None,
        scheduled_at: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update an existing notification template."""
        # First check if template exists and can be edited
        existing = await self.get_by_id(template_id)
        if not existing:
            return None

        if existing["status"] not in ("draft", "scheduled"):
            raise ValueError(f"Cannot edit notification in status: {existing['status']}")

        # Build update data
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if message is not None:
            update_data["message"] = message
        if notification_type is not None:
            update_data["notification_type"] = notification_type
        if channel is not None:
            update_data["channel"] = channel
        if target_users is not None:
            update_data["target_users"] = target_users
        if target_tiers is not None:
            update_data["target_tiers"] = target_tiers
        if scheduled_at is not None:
            update_data["scheduled_at"] = scheduled_at
            update_data["status"] = "scheduled"

        if not update_data:
            return existing

        result = await self.client.table(self.TABLE_NAME).update(
            update_data
        ).eq("id", template_id).execute()

        if not result.data:
            return None

        return self._transform_row(result.data[0])

    @retry_on_network_error()
    async def delete(self, template_id: str) -> bool:
        """Delete a notification template."""
        # Check if it can be deleted (only draft/scheduled)
        existing = await self.get_by_id(template_id)
        if not existing:
            return False

        if existing["status"] not in ("draft", "scheduled"):
            raise ValueError(f"Cannot delete notification in status: {existing['status']}")

        result = await self.client.table(self.TABLE_NAME).delete().eq(
            "id", template_id
        ).execute()

        return len(result.data) > 0 if result.data else False

    @retry_on_network_error()
    async def mark_as_sent(
        self,
        template_id: str,
        total_recipients: int,
        delivered: int = 0,
        failed: int = 0
    ) -> Optional[Dict[str, Any]]:
        """Mark template as sent with statistics."""
        stats = {
            "total_recipients": total_recipients,
            "delivered": delivered,
            "read": 0,
            "failed": failed,
        }

        result = await self.client.table(self.TABLE_NAME).update({
            "status": "sent",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "stats": stats,
        }).eq("id", template_id).execute()

        if not result.data:
            return None

        return self._transform_row(result.data[0])

    @retry_on_network_error()
    async def get_pending_scheduled(self) -> List[Dict[str, Any]]:
        """Get all scheduled notifications that are due to be sent."""
        now = datetime.now(timezone.utc).isoformat()

        result = await self.client.table(self.TABLE_NAME).select("*").eq(
            "status", "scheduled"
        ).lte("scheduled_at", now).execute()

        return [self._transform_row(row) for row in (result.data or [])]

    def _transform_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform database row to API response format.

        Maps database column names to frontend expected format.
        """
        stats = row.get("stats") or {}
        if isinstance(stats, str):
            stats = json.loads(stats)

        return {
            "id": row["id"],
            "title": row["title"],
            "message": row["message"],
            "type": row.get("notification_type", "info"),
            "channel": row.get("channel", "in_app"),
            "status": row.get("status", "draft"),
            "target_users": row.get("target_users"),
            "target_tiers": row.get("target_tiers"),
            "scheduled_at": row.get("scheduled_at"),
            "sent_at": row.get("sent_at"),
            "created_by": row.get("created_by", ""),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
            "stats": stats if stats else None,
        }
