"""
Admin Notifications Router - Notification management endpoints for admins

@module api.admin.notifications
@version 3.25

Changes:
- v3.25: Security improvements
  - NTF-MEDIUM-1: Added rate limiting to GET endpoints
  - NTF-MEDIUM-2: Migrated from page to offset pagination
  - NTF-MEDIUM-3: Added target_group enum validation
  - NTF-MEDIUM-4: Added notification_type enum validation
  - NTF-LOW-1: Added field length limits (title, content, user_id)
  - NTF-LOW-2: Added user_ids list max length validation in schema

Endpoints:
- POST /api/admin/broadcast - Send broadcast notification
- POST /api/admin/notification/send - Send to single user
- POST /api/admin/notification/batch - Send to multiple users
- GET /api/admin/notification/stats - Get notification stats
- GET /api/admin/notification/history - Get notification history
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, Depends, Query
from pydantic import BaseModel, Field, field_validator

from core.database import get_database_client
from infrastructure.repositories import (
    SupabaseNotificationRepository,
    SupabaseAdminUsersRepository,
    SupabaseAdminStatsRepository,
)
from infrastructure.rate_limiter import limiter
from dependencies import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["admin-notifications-v2"])


# ==========================================
# Constants (v3.25)
# ==========================================

# v3.25: NTF-MEDIUM-3 - Valid target groups
VALID_TARGET_GROUPS = {"all", "free", "starter", "pro"}

# v3.25: NTF-MEDIUM-4 - Valid notification types
VALID_NOTIFICATION_TYPES = {"system", "marketing", "alert", "update", "promotion"}


# ==========================================
# Request Models (v3.25: Added field validation)
# ==========================================

class AdminBroadcastRequest(BaseModel):
    # v3.25: NTF-LOW-1 - Field length limits
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=5000)
    target_group: Optional[str] = Field("all", max_length=20)

    # v3.25: NTF-MEDIUM-3 - target_group enum validation
    @field_validator("target_group")
    @classmethod
    def validate_target_group(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_TARGET_GROUPS:
            raise ValueError(f"Invalid target_group. Must be one of: {', '.join(VALID_TARGET_GROUPS)}")
        return v


class AdminSendNotificationRequest(BaseModel):
    # v3.25: NTF-LOW-1 - Field length limits
    user_id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=5000)
    notification_type: Optional[str] = Field("system", max_length=20)

    # v3.25: NTF-MEDIUM-4 - notification_type enum validation
    @field_validator("notification_type")
    @classmethod
    def validate_notification_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_NOTIFICATION_TYPES:
            raise ValueError(f"Invalid notification_type. Must be one of: {', '.join(VALID_NOTIFICATION_TYPES)}")
        return v


class AdminBatchNotificationRequest(BaseModel):
    # v3.25: NTF-LOW-2 - user_ids list max length validation
    user_ids: List[str] = Field(..., max_length=100)
    # v3.25: NTF-LOW-1 - Field length limits
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=5000)
    notification_type: Optional[str] = Field("system", max_length=20)

    # v3.25: NTF-MEDIUM-4 - notification_type enum validation
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
    db_client = get_database_client()
    notification_repo = SupabaseNotificationRepository(db_client)
    stats_repo = SupabaseAdminStatsRepository(db_client)
    admin_users_repo = SupabaseAdminUsersRepository(db_client)

    notification = await notification_repo.create_broadcast(req.title, req.content, req.target_group)
    await stats_repo.log_user_event(admin["id"], "admin_broadcast", {
        "target_group": req.target_group,
        "title": req.title
    })
    await admin_users_repo.admin_log_operation(
        admin_id=admin["id"],
        operation_type="broadcast",
        target_user_id=None,
        details=f"Broadcast to {req.target_group}: {req.title[:50]}",
        reason=None
    )
    return notification


@router.post("/notification/send")
@limiter.limit("30/minute")
async def adm_send_notification(request: Request, req: AdminSendNotificationRequest, admin: dict = Depends(require_admin)):
    """Send a notification to a single user."""
    db_client = get_database_client()
    notification_repo = SupabaseNotificationRepository(db_client)
    stats_repo = SupabaseAdminStatsRepository(db_client)
    admin_users_repo = SupabaseAdminUsersRepository(db_client)

    notification = await notification_repo.send_notification_to_user(
        user_id=req.user_id,
        title=req.title,
        content=req.content,
        notification_type=req.notification_type
    )

    if not notification:
        raise HTTPException(500, "Failed to send notification")

    await stats_repo.log_user_event(admin["id"], "admin_notification_send", {
        "target_user": req.user_id,
        "title": req.title
    })

    await admin_users_repo.admin_log_operation(
        admin_id=admin["id"],
        operation_type="notification_send",
        target_user_id=req.user_id,
        details=f"Notification: {req.title[:50]}",
        reason=None
    )

    return {"status": "sent", "notification": notification}


@router.post("/notification/batch")
@limiter.limit("10/minute")
async def adm_batch_notification(request: Request, req: AdminBatchNotificationRequest, admin: dict = Depends(require_admin)):
    """Send notifications to multiple users."""
    if len(req.user_ids) > 100:
        raise HTTPException(400, "Cannot send to more than 100 users at once")

    db_client = get_database_client()
    notification_repo = SupabaseNotificationRepository(db_client)
    stats_repo = SupabaseAdminStatsRepository(db_client)
    admin_users_repo = SupabaseAdminUsersRepository(db_client)

    notifications = await notification_repo.send_notification_to_users(
        user_ids=req.user_ids,
        title=req.title,
        content=req.content,
        notification_type=req.notification_type
    )

    await stats_repo.log_user_event(admin["id"], "admin_notification_batch", {
        "user_count": len(req.user_ids),
        "title": req.title
    })

    await admin_users_repo.admin_log_operation(
        admin_id=admin["id"],
        operation_type="notification_batch",
        target_user_id=None,
        details=f"Batch notification to {len(req.user_ids)} users: {req.title[:50]}",
        reason=None
    )

    return {"status": "sent", "count": len(notifications)}


# v3.25: NTF-MEDIUM-1 - Added rate limiting
@router.get("/notification/stats")
@limiter.limit("30/minute")
async def adm_notification_stats(request: Request, admin: dict = Depends(require_admin)):
    """Fetch notification statistics."""
    db_client = get_database_client()
    notification_repo = SupabaseNotificationRepository(db_client)
    return await notification_repo.get_all_notification_stats()


# v3.25: NTF-MEDIUM-1 - Added rate limiting
# v3.25: NTF-MEDIUM-2 - Migrated from page to offset pagination
@router.get("/notification/history")
@limiter.limit("30/minute")
async def adm_notification_history(
    request: Request,
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return (1-100)"),
    admin: dict = Depends(require_admin)
):
    """Fetch notification history."""
    db_client = get_database_client()
    notification_repo = SupabaseNotificationRepository(db_client)
    return await notification_repo.get_notification_history(offset=offset, limit=limit)
