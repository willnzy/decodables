"""
Infrastructure - Activity Logger.

Provides activity logging functionality for user actions.

@module infrastructure.logging.activity_logger
@version 2.0.0 (AsyncClient Migration - Phase 6)

v2.0 Changes:
- Migrated to AsyncClient for native async/await
- Removed run_in_threadpool wrappers
- Deprecated log_activity (sync version)
- All logging now fully async

Usage:
    # Async context (recommended):
    await log_activity_async(user_id, "action", metadata)
"""

import logging
from typing import Dict, Any, Optional

from core.database import get_async_db_client

logger = logging.getLogger(__name__)


async def log_activity_async(
    user_id: str, action: str, metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log user activity to activity_logs table (async version).

    v2.0: Now uses AsyncClient with native async/await.

    Args:
        user_id: User ID performing the action
        action: Action type (e.g., "project_created", "asset_uploaded")
        metadata: Optional metadata dict with additional context

    Returns:
        None (logs warning if fails)
    """
    try:
        client = await get_async_db_client()
        if not client:
            logger.warning("AsyncClient not available for activity logging")
            return

        await client.table("activity_logs").insert({
            "user_id": user_id,
            "action": action,
            "metadata": metadata or {}
        }).execute()
    except Exception as e:
        logger.warning(f"Failed to log activity: {e}")


# Deprecated: Sync version removed in v2.0
# Use log_activity_async() instead
def log_activity(user_id: str, action: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """
    DEPRECATED in v2.0: Use log_activity_async() instead.

    This sync version is no longer supported.
    Raises RuntimeError to prevent accidental usage.
    """
    raise RuntimeError(
        "log_activity() is deprecated in v2.0. Use log_activity_async() instead."
    )


async def log_webhook_operation(
    operation_type: str,
    source: str,  # "stripe" or "clerk"
    target_user_id: Optional[str] = None,
    details: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    target_type: str = "user",  # v3.31: 添加默认值以满足数据库 NOT NULL 约束
) -> None:
    """
    Log webhook-driven operations to admin_operations table.

    Uses special admin ID "system_webhook" for automated actions.
    Added in Phase 4 - Task 9 (Activity Logging).

    v2.0: Now uses AsyncClient for repository operations.
    v3.31: Added target_type parameter with default "user" to satisfy NOT NULL constraint.

    Args:
        operation_type: Type of webhook operation (webhook_subscription_create, etc.)
        source: Webhook source ("stripe" or "clerk")
        target_user_id: Affected user ID
        details: Human-readable description
        metadata: Event data (subscription_id, amount, etc.)
        target_type: Resource type (default: "user")

    Example:
        await log_webhook_operation(
            operation_type="webhook_subscription_create",
            source="stripe",
            target_user_id="user_123",
            details="Subscription created",
            metadata={"subscription_id": "sub_xyz", "amount": 999}
        )

    Note:
        Uses graceful degradation - webhook processing won't fail if logging fails.
    """
    from infrastructure.repositories.admin_repository import SupabaseAdminUsersRepository

    WEBHOOK_SYSTEM_ADMIN_ID = "system_webhook"  # Special admin ID for automated actions

    try:
        # v2.0: Use AsyncClient from global singleton
        client = await get_async_db_client()
        if not client:
            logger.warning("AsyncClient not available for webhook logging")
            return

        admin_repo = SupabaseAdminUsersRepository(client)

        await admin_repo.admin_log_operation(
            admin_id=WEBHOOK_SYSTEM_ADMIN_ID,
            operation_type=operation_type,
            target_user_id=target_user_id,
            target_type=target_type,  # v3.31: 传递 target_type 参数
            source=source,
            details=details,
            metadata=metadata,
        )
    except Exception as e:
        logger.warning(f"Failed to log webhook operation {operation_type}: {e}")
        # Don't fail the webhook processing - graceful degradation
