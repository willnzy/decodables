"""
Infrastructure - Activity Logger.

Provides activity logging functionality for user actions.

@module infrastructure.logging.activity_logger
@version 1.0.0
"""

import logging
from typing import Dict, Any, Optional
from core.database import supabase

logger = logging.getLogger(__name__)


def log_activity(user_id: str, action: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """
    Log user activity to activity_logs table.

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
