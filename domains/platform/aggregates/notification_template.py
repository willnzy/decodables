"""
NotificationTemplate Aggregate - Admin notification template management.

@module domains.platform.aggregates.notification_template
@version 1.0.0

This is the aggregate root for admin notification templates.
Supports draft → scheduled → sent workflow for notifications.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum


class NotificationType(str, Enum):
    """Notification type enum."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    ANNOUNCEMENT = "announcement"
    SYSTEM = "system"
    ALERT = "alert"
    PROMO = "promo"


class NotificationChannel(str, Enum):
    """Notification delivery channel enum."""
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"
    ALL = "all"


class NotificationStatus(str, Enum):
    """Notification status enum."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENT = "sent"
    FAILED = "failed"


@dataclass
class NotificationStats:
    """Notification delivery statistics."""
    total_recipients: int = 0
    delivered: int = 0
    read: int = 0
    failed: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "total_recipients": self.total_recipients,
            "delivered": self.delivered,
            "read": self.read,
            "failed": self.failed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotificationStats":
        return cls(
            total_recipients=data.get("total_recipients", 0),
            delivered=data.get("delivered", 0),
            read=data.get("read", 0),
            failed=data.get("failed", 0),
        )


@dataclass
class NotificationTemplate:
    """
    Aggregate root for admin notification template management.

    Supports:
    - Draft creation and editing
    - Scheduled sending
    - Targeting by users or tiers
    - Delivery statistics tracking
    """
    id: str
    title: str
    message: str
    notification_type: NotificationType = NotificationType.INFO
    channel: NotificationChannel = NotificationChannel.IN_APP
    status: NotificationStatus = NotificationStatus.DRAFT
    target_users: Optional[List[str]] = None
    target_tiers: Optional[List[str]] = None
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    stats: NotificationStats = field(default_factory=NotificationStats)

    @classmethod
    def create_draft(
        cls,
        title: str,
        message: str,
        notification_type: str = "info",
        channel: str = "in_app",
        target_users: Optional[List[str]] = None,
        target_tiers: Optional[List[str]] = None,
        scheduled_at: Optional[datetime] = None,
        created_by: str = "",
    ) -> "NotificationTemplate":
        """
        Factory method to create a new draft notification.

        Args:
            title: Notification title
            message: Notification content
            notification_type: Type (info/warning/error/success/announcement)
            channel: Delivery channel (in_app/email/push/all)
            target_users: List of specific user IDs
            target_tiers: List of tier codes (t1/t2/t3)
            scheduled_at: Optional scheduled send time
            created_by: Admin user ID

        Returns:
            New NotificationTemplate instance in draft status
        """
        from uuid import uuid4

        now = datetime.now(timezone.utc)
        status = NotificationStatus.SCHEDULED if scheduled_at else NotificationStatus.DRAFT

        return cls(
            id=str(uuid4()),
            title=title,
            message=message,
            notification_type=NotificationType(notification_type),
            channel=NotificationChannel(channel),
            status=status,
            target_users=target_users,
            target_tiers=target_tiers,
            scheduled_at=scheduled_at,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "NotificationTemplate":
        """
        Reconstruct from database row.

        Args:
            row: Database record dict

        Returns:
            NotificationTemplate instance
        """
        stats_data = row.get("stats") or {}
        if isinstance(stats_data, str):
            import json
            stats_data = json.loads(stats_data)

        return cls(
            id=row["id"],
            title=row["title"],
            message=row["message"],
            notification_type=NotificationType(row.get("notification_type", "info")),
            channel=NotificationChannel(row.get("channel", "in_app")),
            status=NotificationStatus(row.get("status", "draft")),
            target_users=row.get("target_users"),
            target_tiers=row.get("target_tiers"),
            scheduled_at=row.get("scheduled_at"),
            sent_at=row.get("sent_at"),
            created_by=row.get("created_by", ""),
            created_at=row.get("created_at") or datetime.now(timezone.utc),
            updated_at=row.get("updated_at") or datetime.now(timezone.utc),
            stats=NotificationStats.from_dict(stats_data),
        )

    @property
    def is_draft(self) -> bool:
        """Check if notification is in draft status."""
        return self.status == NotificationStatus.DRAFT

    @property
    def is_scheduled(self) -> bool:
        """Check if notification is scheduled."""
        return self.status == NotificationStatus.SCHEDULED

    @property
    def is_sent(self) -> bool:
        """Check if notification has been sent."""
        return self.status == NotificationStatus.SENT

    @property
    def can_edit(self) -> bool:
        """Check if notification can be edited."""
        return self.status in (NotificationStatus.DRAFT, NotificationStatus.SCHEDULED)

    @property
    def can_send(self) -> bool:
        """Check if notification can be sent."""
        return self.status in (NotificationStatus.DRAFT, NotificationStatus.SCHEDULED)

    def update(
        self,
        title: Optional[str] = None,
        message: Optional[str] = None,
        notification_type: Optional[str] = None,
        channel: Optional[str] = None,
        target_users: Optional[List[str]] = None,
        target_tiers: Optional[List[str]] = None,
        scheduled_at: Optional[datetime] = None,
    ):
        """
        Update notification template fields.

        Raises:
            ValueError: If notification cannot be edited
        """
        if not self.can_edit:
            raise ValueError(f"Cannot edit notification in status: {self.status.value}")

        if title is not None:
            self.title = title
        if message is not None:
            self.message = message
        if notification_type is not None:
            self.notification_type = NotificationType(notification_type)
        if channel is not None:
            self.channel = NotificationChannel(channel)
        if target_users is not None:
            self.target_users = target_users
        if target_tiers is not None:
            self.target_tiers = target_tiers
        if scheduled_at is not None:
            self.scheduled_at = scheduled_at
            self.status = NotificationStatus.SCHEDULED

        self.updated_at = datetime.now(timezone.utc)

    def mark_as_sent(self, total_recipients: int, delivered: int = 0, failed: int = 0):
        """
        Mark notification as sent with statistics.

        Args:
            total_recipients: Total number of recipients
            delivered: Number of successful deliveries
            failed: Number of failed deliveries
        """
        self.status = NotificationStatus.SENT
        self.sent_at = datetime.now(timezone.utc)
        self.stats = NotificationStats(
            total_recipients=total_recipients,
            delivered=delivered,
            read=0,
            failed=failed,
        )
        self.updated_at = datetime.now(timezone.utc)

    def mark_as_failed(self, error_message: Optional[str] = None):
        """Mark notification as failed to send."""
        self.status = NotificationStatus.FAILED
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "type": self.notification_type.value,
            "channel": self.channel.value,
            "status": self.status.value,
            "target_users": self.target_users,
            "target_tiers": self.target_tiers,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "stats": self.stats.to_dict() if self.stats else None,
        }
