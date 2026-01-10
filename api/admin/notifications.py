"""
Admin Notifications Router - Notification management endpoints for admins

@module api.admin.notifications
@version 3.30 (DDD Migration)

Changes:
- v3.30: Complete DDD Migration (NTF-CRITICAL-1, NTF-CRITICAL-2, NTF-CRITICAL-3)
  - API → Domain Service → Repository
  - Removed direct Repository calls from API
  - Constants moved to domains/platform/notifications/constants.py
  - Audit logging moved to Service layer
  - All endpoints call Domain Service

- v3.25: Security improvements
  - NTF-MEDIUM-1: Added rate limiting to GET endpoints
  - NTF-MEDIUM-2: Migrated from page to offset pagination
  - NTF-MEDIUM-3: Added target_group enum validation
  - NTF-MEDIUM-4: Added notification_type enum validation
  - NTF-LOW-1: Added field length limits (title, content, user_id)
  - NTF-LOW-2: Added user_ids list max length validation in schema

Endpoints:
- POST /broadcast - Send broadcast notification
- POST /notification/send - Send to single user
- POST /notification/batch - Send to multiple users
- GET /notification/stats - Get notification stats
- GET /notification/history - Get notification history
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, Depends, Query
from pydantic import BaseModel, Field, field_validator

from infrastructure.rate_limiter import limiter
from dependencies import require_admin

# v3.30: Import from Domain layer (DDD Migration)
from domains.platform.notifications import (
    send_broadcast,
    send_to_user,
    send_to_users,
    get_stats,
    get_history,
)
from domains.platform.notifications.constants import (
    VALID_TARGET_GROUPS,
    VALID_NOTIFICATION_TYPES,
    TITLE_MIN_LENGTH,
    TITLE_MAX_LENGTH,
    CONTENT_MIN_LENGTH,
    CONTENT_MAX_LENGTH,
    USER_ID_MIN_LENGTH,
    USER_ID_MAX_LENGTH,
    FIELD_MAX_LENGTH,
    BATCH_MAX_USERS,
    DEFAULT_LIMIT,
    MAX_LIMIT,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["admin-notifications-v2"])


# ==========================================
# Request Models
# ==========================================

class AdminBroadcastRequest(BaseModel):
    title: str = Field(..., min_length=TITLE_MIN_LENGTH, max_length=TITLE_MAX_LENGTH)
    content: str = Field(..., min_length=CONTENT_MIN_LENGTH, max_length=CONTENT_MAX_LENGTH)
    target_group: Optional[str] = Field("all", max_length=FIELD_MAX_LENGTH)

    @field_validator("target_group")
    @classmethod
    def validate_target_group(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_TARGET_GROUPS:
            raise ValueError(f"Invalid target_group. Must be one of: {', '.join(VALID_TARGET_GROUPS)}")
        return v


class AdminSendNotificationRequest(BaseModel):
    user_id: str = Field(..., min_length=USER_ID_MIN_LENGTH, max_length=USER_ID_MAX_LENGTH)
    title: str = Field(..., min_length=TITLE_MIN_LENGTH, max_length=TITLE_MAX_LENGTH)
    content: str = Field(..., min_length=CONTENT_MIN_LENGTH, max_length=CONTENT_MAX_LENGTH)
    notification_type: Optional[str] = Field("system", max_length=FIELD_MAX_LENGTH)

    @field_validator("notification_type")
    @classmethod
    def validate_notification_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_NOTIFICATION_TYPES:
            raise ValueError(f"Invalid notification_type. Must be one of: {', '.join(VALID_NOTIFICATION_TYPES)}")
        return v


class AdminBatchNotificationRequest(BaseModel):
    user_ids: List[str] = Field(..., max_length=BATCH_MAX_USERS)
    title: str = Field(..., min_length=TITLE_MIN_LENGTH, max_length=TITLE_MAX_LENGTH)
    content: str = Field(..., min_length=CONTENT_MIN_LENGTH, max_length=CONTENT_MAX_LENGTH)
    notification_type: Optional[str] = Field("system", max_length=FIELD_MAX_LENGTH)

    @field_validator("notification_type")
    @classmethod
    def validate_notification_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_NOTIFICATION_TYPES:
            raise ValueError(f"Invalid notification_type. Must be one of: {', '.join(VALID_NOTIFICATION_TYPES)}")
        return v


# ==========================================
# Notification Endpoints
# ==========================================

@router.post("/broadcast")
@limiter.limit("5/minute")
async def adm_broadcast(request: Request, req: AdminBroadcastRequest, admin: dict = Depends(require_admin)):
    """
    Send a system-wide broadcast notification to targeted user groups.

    Broadcasts notification to all users or specific user groups (by tier). Creates
    notification records in bulk and triggers real-time delivery. Audit logs the action.

    Args:
        req: Broadcast notification payload
            - title: Notification title (1-200 chars)
            - content: Notification message (1-1000 chars)
            - target_group: Target audience (default: "all")
                Valid values: "all", "t1", "t2", "t3", "free", "paid"

    Returns:
        Dict containing:
            - success: true
            - message: Confirmation message
            - sent_count: Number of users notification was sent to
            - target_group: Target group used

    Raises:
        400: Invalid target_group value or validation error
        401: Unauthorized (not admin)
        500: Database error or notification delivery failure

    Security:
        - Admin role required
        - Rate limit: 5 requests per minute (prevent spam)
        - Audit log created with admin_id
        - Bulk insert optimized for performance

    Example:
        POST /api/v2/admin/notifications/broadcast
        {
            "title": "System Maintenance",
            "content": "Scheduled maintenance on Sunday 2AM-4AM UTC",
            "target_group": "all"
        }
    """
    try:
        # v3.30: Call Domain Service
        result = await send_broadcast(
            title=req.title,
            content=req.content,
            target_group=req.target_group,
            admin_id=admin["id"],
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send broadcast: {e}")
        raise HTTPException(500, "Failed to send broadcast notification")


@router.post("/notification/send")
@limiter.limit("30/minute")
async def adm_send_notification(request: Request, req: AdminSendNotificationRequest, admin: dict = Depends(require_admin)):
    """
    Send a notification to a single user.

    Creates and delivers a notification to a specific user by user_id. Supports
    different notification types (system, announcement, alert, promo). Triggers
    real-time delivery and creates audit log.

    Args:
        req: Notification payload
            - user_id: Target user ID (Clerk format: user_2abc...)
            - title: Notification title (1-200 chars)
            - content: Notification message (1-1000 chars)
            - notification_type: Type of notification (default: "system")
                Valid values: "system", "announcement", "alert", "promo"

    Returns:
        Dict containing:
            - success: true
            - notification_id: Created notification UUID
            - user_id: Target user ID
            - delivered: Whether real-time delivery succeeded

    Raises:
        400: Invalid user_id format or notification_type value
        404: User not found (user_id doesn't exist)
        401: Unauthorized (not admin)
        500: Database error or delivery failure

    Security:
        - Admin role required
        - Rate limit: 30 requests per minute
        - User existence validated
        - Audit log created

    Example:
        POST /api/v2/admin/notifications/notification/send
        {
            "user_id": "user_2abc3def4ghi",
            "title": "Welcome Bonus",
            "content": "You've received 50 bonus credits!",
            "notification_type": "promo"
        }
    """
    try:
        # v3.30: Call Domain Service
        result = await send_to_user(
            user_id=req.user_id,
            title=req.title,
            content=req.content,
            notification_type=req.notification_type,
            admin_id=admin["id"],
        )

        if not result:
            raise HTTPException(500, "Failed to send notification")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        raise HTTPException(500, "Failed to send notification")


@router.post("/notification/batch")
@limiter.limit("10/minute")
async def adm_batch_notification(request: Request, req: AdminBatchNotificationRequest, admin: dict = Depends(require_admin)):
    """
    Send notifications to multiple specific users (batch operation).

    Creates and delivers the same notification to multiple users by user_ids list.
    Processes in bulk for efficiency. Supports partial success (some deliveries may fail).

    Args:
        req: Batch notification payload
            - user_ids: List of target user IDs (max 100 users per request)
            - title: Notification title (1-200 chars)
            - content: Notification message (1-1000 chars)
            - notification_type: Type of notification (default: "system")
                Valid values: "system", "announcement", "alert", "promo"

    Returns:
        Dict containing:
            - success: true
            - sent_count: Number of notifications successfully sent
            - failed_count: Number of failed deliveries
            - total_users: Total user_ids in request
            - failed_user_ids: List of user_ids that failed (if any)

    Raises:
        400: user_ids exceeds 100, invalid notification_type, or empty user_ids list
        401: Unauthorized (not admin)
        500: Complete failure (all deliveries failed)

    Security:
        - Admin role required
        - Rate limit: 10 requests per minute (prevent abuse)
        - Max 100 users per batch (BATCH_MAX_USERS constant)
        - Partial failures don't raise errors (check response)
        - Audit log created

    Example:
        POST /api/v2/admin/notifications/notification/batch
        {
            "user_ids": ["user_2abc", "user_2def", "user_2ghi"],
            "title": "New Feature Announcement",
            "content": "Check out our new editor features!",
            "notification_type": "announcement"
        }

        Response:
        {
            "success": true,
            "sent_count": 2,
            "failed_count": 1,
            "total_users": 3,
            "failed_user_ids": ["user_2def"]
        }
    """
    if len(req.user_ids) > BATCH_MAX_USERS:
        raise HTTPException(400, f"Cannot send to more than {BATCH_MAX_USERS} users at once")

    try:
        # v3.30: Call Domain Service
        result = await send_to_users(
            user_ids=req.user_ids,
            title=req.title,
            content=req.content,
            notification_type=req.notification_type,
            admin_id=admin["id"],
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send batch notification: {e}")
        raise HTTPException(500, "Failed to send batch notification")


@router.get("/notification/stats")
@limiter.limit("30/minute")
async def adm_notification_stats(request: Request, admin: dict = Depends(require_admin)):
    """
    Get notification statistics and metrics.

    Returns aggregate statistics about notification delivery, types, and
    user engagement. Useful for monitoring system usage and effectiveness.

    Returns:
        Dict containing:
            - total_sent: Total notifications sent (all time)
            - sent_today: Notifications sent today
            - sent_this_week: Notifications sent this week
            - sent_this_month: Notifications sent this month
            - by_type: Breakdown by notification_type (system/announcement/alert/promo)
            - by_target_group: Breakdown by target group (all/t1/t2/t3)
            - delivery_rate: Percentage of successful deliveries
            - read_rate: Percentage of notifications read by users
            - avg_time_to_read: Average time until user reads notification

    Raises:
        401: Unauthorized (not admin)
        500: Database error

    Security:
        - Admin role required
        - Rate limit: 30 requests per minute
        - Read-only operation
        - No sensitive data exposed

    Example:
        GET /api/v2/admin/notifications/notification/stats

        Response:
        {
            "total_sent": 15420,
            "sent_today": 245,
            "sent_this_week": 1832,
            "sent_this_month": 7291,
            "by_type": {
                "system": 8500,
                "announcement": 4200,
                "alert": 1800,
                "promo": 920
            },
            "delivery_rate": 99.2,
            "read_rate": 67.5
        }
    """
    try:
        # v3.30: Call Domain Service
        return await get_stats()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get notification stats: {e}")
        raise HTTPException(500, "Failed to get notification statistics")


@router.get("/notification/history")
@limiter.limit("30/minute")
async def adm_notification_history(
    request: Request,
    offset: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description=f"Maximum number of records to return (1-{MAX_LIMIT})"),
    admin: dict = Depends(require_admin)
):
    """
    Get notification send history with pagination.

    Returns chronological list of all sent notifications with delivery status
    and metadata. Supports pagination for large result sets.

    Args:
        offset: Skip first N records (default: 0)
        limit: Return max N records (default: 20, max: 100)

    Returns:
        Dict containing:
            - data: List of notification records including:
                - id: Notification UUID
                - title: Notification title
                - content: Notification content
                - notification_type: Type (system/announcement/alert/promo)
                - target_group: Target audience (all/t1/t2/t3) or null for single/batch
                - user_id: Specific user (for single sends) or null
                - user_ids: User list (for batch sends) or null
                - sent_count: Number of users sent to
                - delivered_count: Number of successful deliveries
                - read_count: Number of users who read notification
                - created_at: Send timestamp
                - created_by: Admin user_id who sent
            - pagination: Object with offset, limit, and total count

    Raises:
        401: Unauthorized (not admin)
        400: Invalid offset or limit values
        500: Database error

    Security:
        - Admin role required
        - Rate limit: 30 requests per minute
        - Ordered by created_at DESC (newest first)
        - No PII exposed (user_ids only for admin)

    Example:
        GET /api/v2/admin/notifications/notification/history?offset=0&limit=50

        Response:
        {
            "data": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "title": "System Maintenance",
                    "notification_type": "system",
                    "target_group": "all",
                    "sent_count": 1542,
                    "delivered_count": 1538,
                    "read_count": 982,
                    "created_at": "2026-01-11T10:30:00Z",
                    "created_by": "admin_user_123"
                }
            ],
            "pagination": {
                "offset": 0,
                "limit": 50,
                "total": 324
            }
        }
    """
    try:
        # v3.30: Call Domain Service
        return await get_history(offset=offset, limit=limit)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get notification history: {e}")
        raise HTTPException(500, "Failed to get notification history")
