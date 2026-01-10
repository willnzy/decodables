"""
Infrastructure - Activity Logger.

Provides activity logging functionality for user actions.

@module infrastructure.logging.activity_logger
@version 1.1.0

Usage:
    # Sync context (legacy):
    log_activity(user_id, "action", metadata)

    # Async context (recommended):
    await log_activity_async(user_id, "action", metadata)

    # Or use run_in_threadpool directly:
    from fastapi.concurrency import run_in_threadpool
    await run_in_threadpool(log_activity, user_id, "action", metadata)
"""

import logging
from typing import Dict, Any, Optional

from fastapi.concurrency import run_in_threadpool

from core.database import supabase

logger = logging.getLogger(__name__)


def log_activity(user_id: str, action: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """
    Log user activity to activity_logs table (synchronous version).

    For async handlers, prefer log_activity_async() or wrap with run_in_threadpool().

    Args:
        user_id: User ID performing the action
        action: Action type (e.g., "project_created", "asset_uploaded")
        metadata: Optional metadata dict with additional context

    Returns:
        None (logs warning if fails)
    """
    if not supabase:
        return

    try:
        supabase.table("activity_logs").insert({
            "user_id": user_id,
            "action": action,
            "metadata": metadata or {}
        }).execute()
    except Exception as e:
        logger.warning(f"Failed to log activity: {e}")


async def log_activity_async(
    user_id: str, action: str, metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log user activity to activity_logs table (async version).

    Uses run_in_threadpool to avoid blocking the event loop.
    This is the recommended way to call from async FastAPI handlers.

    Args:
        user_id: User ID performing the action
        action: Action type (e.g., "project_created", "asset_uploaded")
        metadata: Optional metadata dict with additional context

    Returns:
        None (logs warning if fails)
    """
    await run_in_threadpool(log_activity, user_id, action, metadata)


async def log_webhook_operation(
    operation_type: str,
    source: str,  # "stripe" or "clerk"
    target_user_id: Optional[str] = None,
    details: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log webhook-driven operations to admin_operations table.

    Uses special admin ID "system_webhook" for automated actions.
    Added in Phase 4 - Task 9 (Activity Logging).

    Args:
        operation_type: Type of webhook operation (webhook_subscription_create, etc.)
        source: Webhook source ("stripe" or "clerk")
        target_user_id: Affected user ID
        details: Human-readable description
        metadata: Event data (subscription_id, amount, etc.)

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
    from core.database import get_database_client
    from infrastructure.repositories.admin_repository import SupabaseAdminUsersRepository

    WEBHOOK_SYSTEM_ADMIN_ID = "system_webhook"  # Special admin ID for automated actions

    try:
        db = get_database_client()
        admin_repo = SupabaseAdminUsersRepository(db)

        await admin_repo.admin_log_operation(
            admin_id=WEBHOOK_SYSTEM_ADMIN_ID,
            operation_type=operation_type,
            target_user_id=target_user_id,
            source=source,
            details=details,
            metadata=metadata,
        )
    except Exception as e:
        logger.warning(f"Failed to log webhook operation {operation_type}: {e}")
        # Don't fail the webhook processing - graceful degradation
