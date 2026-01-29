"""
Notifications 模块 Domain Service - 通知管理业务逻辑

@module domains.platform.notifications.service
@version 3.33 (Admin Template CRUD Support)

Changes in v3.33:
- Added CRUD functions for admin notification templates
- Added get_template, list_templates, create_template, update_template, delete_template
- Added send_template function to send a template immediately

Changes in v3.32:
- Added Repository dependency injection (Task 2)
- Added factory functions for Repository instances
- All service functions now accept optional Repository parameters
- Improved testability and SOLID compliance

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
- API → Service → Repository (with DI support)
"""

import logging

from core.database import get_async_db_client
from typing import Optional, List, Dict, Any

from core.audit import audit_log
from domains.platform.repository import INotificationRepository, INotificationTemplateRepository

logger = logging.getLogger(__name__)


# ==========================================
# Repository Factory Functions
# ==========================================

async def _get_notification_repo(repo: Optional[INotificationRepository] = None) -> INotificationRepository:
    """
    获取 NotificationRepository 实例 (依赖注入或默认实例).

    v3.33: Fixed async function declaration (SyntaxError fix).

    Args:
        repo: 可选的 Repository 实例 (用于依赖注入/测试)

    Returns:
        INotificationRepository 实例
    """
    if repo:
        return repo

    from infrastructure.repositories import SupabaseNotificationRepository

    db_client = await get_async_db_client()
    return SupabaseNotificationRepository(db_client)


async def _get_stats_repo(repo=None):
    """
    获取 AdminStatsRepository 实例 (依赖注入或默认实例).

    v3.33: Fixed async function declaration (SyntaxError fix).

    Args:
        repo: 可选的 Repository 实例 (用于依赖注入/测试)

    Returns:
        AdminStatsRepository 实例
    """
    if repo:
        return repo

    from infrastructure.repositories import SupabaseAdminStatsRepository

    db_client = await get_async_db_client()
    return SupabaseAdminStatsRepository(db_client)


async def _get_admin_users_repo(repo=None):
    """
    获取 AdminUsersRepository 实例 (依赖注入或默认实例).

    v3.33: Fixed async function declaration (SyntaxError fix).

    Args:
        repo: 可选的 Repository 实例 (用于依赖注入/测试)

    Returns:
        AdminUsersRepository 实例
    """
    if repo:
        return repo

    from infrastructure.repositories import SupabaseAdminUsersRepository

    db_client = await get_async_db_client()
    return SupabaseAdminUsersRepository(db_client)


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
    notification_repo: Optional[INotificationRepository] = None,
) -> Dict[str, Any]:
    """
    发送广播通知.

    v3.32: Added Repository dependency injection
    v3.31: Applied @audit_log decorator
    v3.30: DDD Migration
    - 从 API 层迁移
    - 从 Repository 层迁移业务逻辑 (NTF-MEDIUM-1)

    Args:
        title: 通知标题
        content: 通知内容
        target_group: 目标用户组 (all/t1/t2/t3)
        admin_id: 管理员 ID
        notification_repo: 可选的 NotificationRepository 实例 (用于依赖注入/测试)

    Returns:
        广播结果
    """
    repo = await _get_notification_repo(notification_repo)

    
    db_client = await get_async_db_client()

    # Business Logic: Query target users based on group
    if target_group == "all":
        users_result = await db_client.table("profiles").select("id").execute()
    else:
        users_result = await db_client.table("profiles").select("id").eq(
            "tier", target_group
        ).execute()

    users = users_result.data or []
    user_ids = [u["id"] for u in users]

    # Create notifications for all users
    notifications = []
    for user_id in user_ids:
        notification = await repo.create_notification(
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
    notification_repo: Optional[INotificationRepository] = None,
) -> Dict[str, Any]:
    """
    发送通知给单个用户.

    v3.32: Added Repository dependency injection
    v3.31: Applied @audit_log decorator
    v3.30: DDD Migration - 从 API 层迁移

    Args:
        user_id: 用户 ID
        title: 通知标题
        content: 通知内容
        notification_type: 通知类型
        admin_id: 管理员 ID
        notification_repo: 可选的 NotificationRepository 实例 (用于依赖注入/测试)

    Returns:
        发送结果
    """
    repo = await _get_notification_repo(notification_repo)

    notification = await repo.send_notification_to_user(
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
    notification_repo: Optional[INotificationRepository] = None,
) -> Dict[str, Any]:
    """
    批量发送通知.

    v3.32: Added Repository dependency injection
    v3.31: Applied @audit_log decorator
    v3.30: DDD Migration - 从 API 层迁移

    Args:
        user_ids: 用户 ID 列表
        title: 通知标题
        content: 通知内容
        notification_type: 通知类型
        admin_id: 管理员 ID
        notification_repo: 可选的 NotificationRepository 实例 (用于依赖注入/测试)

    Returns:
        发送结果
    """
    repo = await _get_notification_repo(notification_repo)

    notifications = await repo.send_notification_to_users(
        user_ids=user_ids,
        title=title,
        content=content,
        notification_type=notification_type
    )

    logger.info(f"[Notifications] Batch notification sent to {len(user_ids)} users by admin {admin_id}")
    return {"status": "sent", "count": len(notifications)}


async def get_stats(
    notification_repo: Optional[INotificationRepository] = None,
) -> Dict[str, Any]:
    """
    获取通知统计.

    v3.32: Added Repository dependency injection
    v3.30: DDD Migration - 从 API 层迁移

    Args:
        notification_repo: 可选的 NotificationRepository 实例 (用于依赖注入/测试)

    Returns:
        统计数据
    """
    repo = await _get_notification_repo(notification_repo)
    return await repo.get_all_notification_stats()


async def get_history(
    offset: int = 0,
    limit: int = 50,
    notification_repo: Optional[INotificationRepository] = None,
) -> Dict[str, Any]:
    """
    获取通知历史.

    v3.32: Added Repository dependency injection
    v3.30: DDD Migration - 从 API 层迁移

    Args:
        offset: 分页偏移
        limit: 分页大小
        notification_repo: 可选的 NotificationRepository 实例 (用于依赖注入/测试)

    Returns:
        通知历史记录
    """
    repo = await _get_notification_repo(notification_repo)
    return await repo.get_notification_history(offset=offset, limit=limit)


# ==========================================
# Admin Notification Template CRUD (v3.33)
# ==========================================

async def _get_template_repo(repo: Optional[INotificationTemplateRepository] = None) -> INotificationTemplateRepository:
    """
    获取 NotificationTemplateRepository 实例 (依赖注入或默认实例).

    Args:
        repo: 可选的 Repository 实例 (用于依赖注入/测试)

    Returns:
        INotificationTemplateRepository 实例
    """
    if repo:
        return repo

    from infrastructure.repositories import SupabaseNotificationTemplateRepository

    db_client = await get_async_db_client()
    return SupabaseNotificationTemplateRepository(db_client)


async def list_templates(
    status: Optional[str] = None,
    offset: int = 0,
    limit: int = 20,
    template_repo: Optional[INotificationTemplateRepository] = None,
) -> Dict[str, Any]:
    """
    获取通知模板列表.

    v3.33: New function for Admin Panel CRUD

    Args:
        status: 状态筛选 (draft/scheduled/sent/failed)
        offset: 分页偏移
        limit: 分页大小
        template_repo: 可选的 Repository 实例 (用于依赖注入/测试)

    Returns:
        Dict with notifications list and total count
    """
    repo = await _get_template_repo(template_repo)
    return await repo.get_list(status=status, offset=offset, limit=limit)


async def get_template(
    template_id: str,
    template_repo: Optional[INotificationTemplateRepository] = None,
) -> Optional[Dict[str, Any]]:
    """
    获取单个通知模板.

    v3.33: New function for Admin Panel CRUD

    Args:
        template_id: 模板 ID
        template_repo: 可选的 Repository 实例 (用于依赖注入/测试)

    Returns:
        Template dict or None if not found
    """
    repo = await _get_template_repo(template_repo)
    return await repo.get_by_id(template_id)


@audit_log(
    operation_type="notification_template_create",
    event_type="admin_notification_template_create",
    get_details=lambda result, **kwargs: f"Created template: {kwargs.get('title', '')[:50]}"
)
async def create_template(
    title: str,
    message: str,
    notification_type: str,
    channel: str,
    admin_id: str,
    target_users: Optional[List[str]] = None,
    target_tiers: Optional[List[str]] = None,
    scheduled_at: Optional[str] = None,
    template_repo: Optional[INotificationTemplateRepository] = None,
) -> Dict[str, Any]:
    """
    创建通知模板.

    v3.33: New function for Admin Panel CRUD

    Args:
        title: 通知标题
        message: 通知内容
        notification_type: 通知类型
        channel: 发送渠道
        admin_id: 管理员 ID
        target_users: 目标用户列表
        target_tiers: 目标 Tier 列表
        scheduled_at: 定时发送时间 (ISO string)
        template_repo: 可选的 Repository 实例 (用于依赖注入/测试)

    Returns:
        Created template dict
    """
    repo = await _get_template_repo(template_repo)
    result = await repo.create(
        title=title,
        message=message,
        notification_type=notification_type,
        channel=channel,
        target_users=target_users,
        target_tiers=target_tiers,
        scheduled_at=scheduled_at,
        created_by=admin_id,
    )

    logger.info(f"[Notifications] Template created by admin {admin_id}: {title[:50]}")
    return result


@audit_log(
    operation_type="notification_template_update",
    event_type="admin_notification_template_update",
    get_details=lambda result, **kwargs: f"Updated template: {kwargs.get('template_id', '')[:36]}"
)
async def update_template(
    template_id: str,
    admin_id: str,
    title: Optional[str] = None,
    message: Optional[str] = None,
    notification_type: Optional[str] = None,
    channel: Optional[str] = None,
    target_users: Optional[List[str]] = None,
    target_tiers: Optional[List[str]] = None,
    scheduled_at: Optional[str] = None,
    template_repo: Optional[INotificationTemplateRepository] = None,
) -> Optional[Dict[str, Any]]:
    """
    更新通知模板.

    v3.33: New function for Admin Panel CRUD

    Args:
        template_id: 模板 ID
        admin_id: 管理员 ID
        title: 新标题
        message: 新内容
        notification_type: 新类型
        channel: 新渠道
        target_users: 新目标用户
        target_tiers: 新目标 Tier
        scheduled_at: 新定时时间
        template_repo: 可选的 Repository 实例 (用于依赖注入/测试)

    Returns:
        Updated template dict or None if not found
    """
    repo = await _get_template_repo(template_repo)
    result = await repo.update(
        template_id=template_id,
        title=title,
        message=message,
        notification_type=notification_type,
        channel=channel,
        target_users=target_users,
        target_tiers=target_tiers,
        scheduled_at=scheduled_at,
    )

    if result:
        logger.info(f"[Notifications] Template {template_id} updated by admin {admin_id}")

    return result


@audit_log(
    operation_type="notification_template_delete",
    event_type="admin_notification_template_delete",
    get_details=lambda result, **kwargs: f"Deleted template: {kwargs.get('template_id', '')[:36]}"
)
async def delete_template(
    template_id: str,
    admin_id: str,
    template_repo: Optional[INotificationTemplateRepository] = None,
) -> bool:
    """
    删除通知模板.

    v3.33: New function for Admin Panel CRUD

    Args:
        template_id: 模板 ID
        admin_id: 管理员 ID
        template_repo: 可选的 Repository 实例 (用于依赖注入/测试)

    Returns:
        True if deleted, False if not found
    """
    repo = await _get_template_repo(template_repo)
    result = await repo.delete(template_id)

    if result:
        logger.info(f"[Notifications] Template {template_id} deleted by admin {admin_id}")

    return result


@audit_log(
    operation_type="notification_template_send",
    event_type="admin_notification_template_send",
    get_details=lambda result, **kwargs: f"Sent template: {kwargs.get('template_id', '')[:36]}, recipients: {result.get('total_recipients', 0) if result else 0}"
)
async def send_template(
    template_id: str,
    admin_id: str,
    template_repo: Optional[INotificationTemplateRepository] = None,
    notification_repo: Optional[INotificationRepository] = None,
) -> Dict[str, Any]:
    """
    发送通知模板.

    v3.33: New function for Admin Panel CRUD
    将模板中的通知发送给目标用户.

    Args:
        template_id: 模板 ID
        admin_id: 管理员 ID
        template_repo: 可选的 Repository 实例 (用于依赖注入/测试)
        notification_repo: 可选的 Repository 实例 (用于依赖注入/测试)

    Returns:
        Dict with send results
    """
    t_repo = await _get_template_repo(template_repo)
    n_repo = await _get_notification_repo(notification_repo)

    # Get the template
    template = await t_repo.get_by_id(template_id)
    if not template:
        raise ValueError(f"Template not found: {template_id}")

    if template["status"] not in ("draft", "scheduled"):
        raise ValueError(f"Cannot send template in status: {template['status']}")

    # Determine target users
    db_client = await get_async_db_client()
    target_user_ids = []

    if template.get("target_users"):
        target_user_ids = template["target_users"]
    elif template.get("target_tiers"):
        # Query users by tier
        for tier in template["target_tiers"]:
            users_result = await db_client.table("profiles").select("id").eq("tier", tier).execute()
            target_user_ids.extend([u["id"] for u in (users_result.data or [])])
    else:
        # Send to all users
        users_result = await db_client.table("profiles").select("id").execute()
        target_user_ids = [u["id"] for u in (users_result.data or [])]

    # Remove duplicates
    target_user_ids = list(set(target_user_ids))

    # Send notifications
    delivered = 0
    failed = 0

    for user_id in target_user_ids:
        try:
            notification = await n_repo.create_notification(
                user_id=user_id,
                title=template["title"],
                message=template["message"],
                notification_type=template.get("type", "info"),
            )
            if notification:
                delivered += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Failed to send notification to {user_id}: {e}")
            failed += 1

    # Mark template as sent
    await t_repo.mark_as_sent(
        template_id=template_id,
        total_recipients=len(target_user_ids),
        delivered=delivered,
        failed=failed,
    )

    result = {
        "success": True,
        "template_id": template_id,
        "total_recipients": len(target_user_ids),
        "delivered": delivered,
        "failed": failed,
    }

    logger.info(f"[Notifications] Template {template_id} sent by admin {admin_id}: {delivered}/{len(target_user_ids)} delivered")
    return result
