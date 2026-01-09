"""
Core Audit Logging Utilities

@module core.audit
@version 1.0.0

Provides unified audit logging mechanism for admin operations.
Replaces scattered audit logging calls throughout the codebase.
"""

import logging
from functools import wraps
from typing import Optional, Callable, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def audit_log(
    operation_type: str,
    event_type: Optional[str] = None,
    get_target_user_id: Optional[Callable] = None,
    get_details: Optional[Callable] = None,
):
    """
    Decorator for automatic audit logging of admin operations.

    Usage:
        @audit_log(
            operation_type="campaign_create",
            event_type="admin_campaign_create",
            get_details=lambda result: f"Campaign: {result['name']}"
        )
        async def create_campaign(..., admin_id: str):
            # Your business logic
            return campaign

    Args:
        operation_type: Operation type for admin_log_operation (e.g., "campaign_create")
        event_type: Event type for stats logging (optional, defaults to operation_type)
        get_target_user_id: Function to extract target_user_id from function args/kwargs
        get_details: Function to generate detail string from function result

    Notes:
        - Decorated function MUST have an `admin_id` parameter
        - Logs are created AFTER successful execution (not on errors)
        - Both admin_log_operation and log_user_event are called
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute the original function
            result = await func(*args, **kwargs)

            # Extract admin_id from kwargs (required)
            admin_id = kwargs.get("admin_id")
            if not admin_id:
                logger.warning(f"[Audit] No admin_id found for {func.__name__}, skipping audit log")
                return result

            # Extract target_user_id if provided
            target_user_id = None
            if get_target_user_id:
                try:
                    target_user_id = get_target_user_id(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"[Audit] Failed to extract target_user_id: {e}")

            # Generate details
            details = None
            if get_details:
                try:
                    details = get_details(result, *args, **kwargs)
                except Exception as e:
                    logger.warning(f"[Audit] Failed to generate details: {e}")
                    details = f"{operation_type} completed"

            # Log to both systems
            try:
                from core.database import get_database_client
                from infrastructure.repositories import (
                    SupabaseAdminStatsRepository,
                    SupabaseAdminUsersRepository,
                )

                db_client = get_database_client()
                stats_repo = SupabaseAdminStatsRepository(db_client)
                admin_users_repo = SupabaseAdminUsersRepository(db_client)

                # Event logging (for metrics/analytics)
                event_data = {
                    "operation": operation_type,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                if target_user_id:
                    event_data["target_user"] = target_user_id

                await stats_repo.log_user_event(
                    admin_id,
                    event_type or operation_type,
                    event_data
                )

                # Operation logging (for audit trail)
                await admin_users_repo.admin_log_operation(
                    admin_id=admin_id,
                    operation_type=operation_type,
                    target_user_id=target_user_id,
                    details=details or f"{operation_type} completed",
                    reason=None
                )

                logger.debug(f"[Audit] Logged {operation_type} by admin {admin_id}")

            except Exception as e:
                # Don't fail the operation if audit logging fails
                logger.error(f"[Audit] Failed to create audit logs: {e}")

            return result

        return wrapper
    return decorator


def audit_log_simple(operation_type: str, detail_template: str = None):
    """
    Simplified audit logging decorator for operations without complex details.

    Usage:
        @audit_log_simple("campaign_delete", "Deleted campaign {campaign_id}")
        async def delete_campaign(campaign_id: str, admin_id: str):
            # Your logic
            return success

    Args:
        operation_type: Operation type string
        detail_template: Template string with {param_name} placeholders
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            admin_id = kwargs.get("admin_id")
            if not admin_id:
                return result

            # Generate details from template
            details = detail_template
            if details:
                try:
                    details = details.format(**kwargs)
                except Exception as e:
                    logger.warning(f"[Audit] Failed to format details template: {e}")
                    details = f"{operation_type} completed"

            try:
                from core.database import get_database_client
                from infrastructure.repositories import (
                    SupabaseAdminStatsRepository,
                    SupabaseAdminUsersRepository,
                )

                db_client = get_database_client()
                stats_repo = SupabaseAdminStatsRepository(db_client)
                admin_users_repo = SupabaseAdminUsersRepository(db_client)

                await stats_repo.log_user_event(admin_id, operation_type, {
                    "operation": operation_type,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

                await admin_users_repo.admin_log_operation(
                    admin_id=admin_id,
                    operation_type=operation_type,
                    target_user_id=None,
                    details=details or f"{operation_type} completed",
                    reason=None
                )

            except Exception as e:
                logger.error(f"[Audit] Failed to create audit logs: {e}")

            return result

        return wrapper
    return decorator
