"""
Notifications 模块 - 通知管理

@module domains.platform.notifications
@version 3.30 (DDD Migration)

This domain handles:
- Broadcast notifications
- Single user notifications
- Batch notifications
- Notification statistics
- Notification history
"""

from domains.platform.notifications.service import (
    send_broadcast,
    send_to_user,
    send_to_users,
    get_stats,
    get_history,
)

__all__ = [
    "send_broadcast",
    "send_to_user",
    "send_to_users",
    "get_stats",
    "get_history",
]
