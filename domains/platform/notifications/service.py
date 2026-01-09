"""
Notifications 模块 Domain Service - 通知管理业务逻辑

@module domains.platform.notifications.service
@version 3.31 (Audit Decorator Migration)

Changes in v3.31:
- Applied @audit_log decorator to 3 functions (Task 1)
- Removed manual audit logging code (-45 lines)
- Simplified service functions by using decorator

Changes in v3.30:
- Complete DDD Migration from api/admin/notifications.py (NTF-CRITICAL-1)
- All business logic moved to Service layer
- API layer only handles HTTP concerns
- Added centralized audit logging (NTF-CRITICAL-3)
- Moved broadcast logic from Repository to Service (NTF-MEDIUM-1)

Architecture:
- API → Service → Repository
"""

import logging
from typing import Optional, List, Dict, Any

from core.audit import audit_log

logger = logging.getLogger(__name__)


# ==========================================
# Notification Operations
# ==========================================

@audit_log(
    operation_type="broadcast",
    event_type="admin_broadcast",
    get_details=lambda result, **kwargs: f"Broadcast to {kwargs.get('target_group')}: {kwargs.get('title', '')[:50]}"
)
async def send_broadcast(
    title: str,
    content: str,
    target_group: str,
    admin_id: str,
) -> Dict[str, Any]:
    """
    发送广播通知.

    v3.31: Applied @audit_log decorator
    v3.30: DDD Migration
    - 从 API 层迁移
    - 从 Repository 层迁移业务逻辑 (NTF-MEDIUM-1)

    Args:
        title: 通知标题
        content: 通知内容
        target_group: 目标用户组 (all/free/starter/pro)
        admin_id: 管理员 ID

    Returns:
        广播结果
    """
    from core.database import get_database_client
    from infrastructure.repositories import SupabaseNotificationRepository

    db_client = get_database_client()
    notification_repo = SupabaseNotificationRepository(db_client)

    # Business Logic: Query target users based on group
    if target_group == "all":
        users_result = db_client.table("profiles").select("id").execute()
    else:
        users_result = db_client.table("profiles").select("id").eq(
            "tier", target_group
        ).execute()

    users = users_result.data or []
    user_ids = [u["id"] for u in users]

    # Create notifications for all users
    notifications = []
    for user_id in user_ids:
        notification = await notification_repo.create_notification(
            user_id=user_id,
            title=title,
            message=content,
            notification_type="system"
        )
        if notification:
            notifications.append(notification)

    result = {
        "target_group": target_group,
        "user_count": len(user_ids),
        "notification_count": len(notifications),
        "title": title
    }

    logger.info(f"[Notifications] Broadcast sent to {len(user_ids)} users by admin {admin_id}")
    return result


@audit_log(
    operation_type="notification_send",
    event_type="admin_notification_send",
    get_target_user_id=lambda *args, **kwargs: kwargs.get("user_id"),
    get_details=lambda result, **kwargs: f"Notification: {kwargs.get('title', '')[:50]}"
)
async def send_to_user(
    user_id: str,
    title: str,
    content: str,
    notification_type: str,
    admin_id: str,
) -> Dict[str, Any]:
    """
    发送通知给单个用户.

    v3.31: Applied @audit_log decorator
    v3.30: DDD Migration - 从 API 层迁移

    Args:
        user_id: 用户 ID
        title: 通知标题
        content: 通知内容
        notification_type: 通知类型
        admin_id: 管理员 ID

    Returns:
        发送结果
    """
    from core.database import get_database_client
    from infrastructure.repositories import SupabaseNotificationRepository

    db_client = get_database_client()
    notification_repo = SupabaseNotificationRepository(db_client)

    notification = await notification_repo.send_notification_to_user(
        user_id=user_id,
        title=title,
        content=content,
        notification_type=notification_type
    )

    if not notification:
        return None

    logger.info(f"[Notifications] Notification sent to user {user_id} by admin {admin_id}")
    return {"status": "sent", "notification": notification}


@audit_log(
    operation_type="notification_batch",
    event_type="admin_notification_batch",
    get_details=lambda result, **kwargs: f"Batch notification to {len(kwargs.get('user_ids', []))} users: {kwargs.get('title', '')[:50]}"
)
async def send_to_users(
    user_ids: List[str],
    title: str,
    content: str,
    notification_type: str,
    admin_id: str,
) -> Dict[str, Any]:
    """
    批量发送通知.

    v3.31: Applied @audit_log decorator
    v3.30: DDD Migration - 从 API 层迁移

    Args:
        user_ids: 用户 ID 列表
        title: 通知标题
        content: 通知内容
        notification_type: 通知类型
        admin_id: 管理员 ID

    Returns:
        发送结果
    """
    from core.database import get_database_client
    from infrastructure.repositories import SupabaseNotificationRepository

    db_client = get_database_client()
    notification_repo = SupabaseNotificationRepository(db_client)

    notifications = await notification_repo.send_notification_to_users(
        user_ids=user_ids,
        title=title,
        content=content,
        notification_type=notification_type
    )

    logger.info(f"[Notifications] Batch notification sent to {len(user_ids)} users by admin {admin_id}")
    return {"status": "sent", "count": len(notifications)}


async def get_stats() -> Dict[str, Any]:
    """
    获取通知统计.

    v3.30: DDD Migration - 从 API 层迁移

    Returns:
        统计数据
    """
    from core.database import get_database_client
    from infrastructure.repositories import SupabaseNotificationRepository

    db_client = get_database_client()
    notification_repo = SupabaseNotificationRepository(db_client)

    return await notification_repo.get_all_notification_stats()


async def get_history(
    offset: int = 0,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    获取通知历史.

    v3.30: DDD Migration - 从 API 层迁移

    Args:
        offset: 分页偏移
        limit: 分页大小

    Returns:
        通知历史记录
    """
    from core.database import get_database_client
    from infrastructure.repositories import SupabaseNotificationRepository

    db_client = get_database_client()
    notification_repo = SupabaseNotificationRepository(db_client)

    return await notification_repo.get_notification_history(offset=offset, limit=limit)
