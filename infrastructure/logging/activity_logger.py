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
