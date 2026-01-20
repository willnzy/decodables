"""
Notifications 模块 - 通知管理

@module domains.platform.notifications
@version 3.33 (Admin Template CRUD Support)

This domain handles:
- Broadcast notifications
- Single user notifications
- Batch notifications
- Notification statistics
- Notification history
- Admin notification templates (CRUD) - v3.33
"""

from domains.platform.notifications.service import (
    # Legacy sending operations
    send_broadcast,
    send_to_user,
    send_to_users,
    get_stats,
    get_history,
    # Admin template CRUD (v3.33)
    list_templates,
    get_template,
    create_template,
    update_template,
    delete_template,
    send_template,
)

__all__ = [
    # Legacy sending operations
    "send_broadcast",
    "send_to_user",
    "send_to_users",
    "get_stats",
    "get_history",
    # Admin template CRUD (v3.33)
    "list_templates",
    "get_template",
    "create_template",
    "update_template",
    "delete_template",
    "send_template",
]
