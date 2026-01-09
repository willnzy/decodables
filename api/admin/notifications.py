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
    """Send a system-wide broadcast notification."""
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
    """Send a notification to a single user."""
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
    """Send notifications to multiple users."""
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
    """Fetch notification statistics."""
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
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description=f"Number of records to return (1-{MAX_LIMIT})"),
    admin: dict = Depends(require_admin)
):
    """Fetch notification history."""
    try:
        # v3.30: Call Domain Service
        return await get_history(offset=offset, limit=limit)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get notification history: {e}")
        raise HTTPException(500, "Failed to get notification history")
