"""
Admin Notifications API - Notification management for admins.

@module api.admin.notifications_api
@version 1.0.0

Endpoints:
- POST /notifications/broadcast - Send broadcast notification
- POST /notifications/send - Send to single user
- POST /notifications/batch - Send to multiple users
- GET /notifications/stats - Get notification stats
- GET /notifications/history - Get notification history
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field

from dependencies import require_admin
from services.db_service import (
    create_broadcast,
    send_notification_to_user,
    send_notification_to_users,
    get_all_notification_stats,
    get_notification_history,
    admin_log_operation,
    log_activity,
)
from services.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["admin-notifications-v2"])


# ==========================================
# Request Models
# ==========================================

class BroadcastRequest(BaseModel):
    """Broadcast notification request."""
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=2000)
    target_group: str = Field("all", pattern="^(all|free|starter|pro)$")


class SendNotificationRequest(BaseModel):
    """Send notification to single user request."""
    user_id: str
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=2000)
    notification_type: str = "system"


class BatchNotificationRequest(BaseModel):
    """Batch notification request."""
    user_ids: List[str] = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=2000)
    notification_type: str = "system"


# ==========================================
# Endpoints
# ==========================================

@router.post("/broadcast")
@limiter.limit("5/minute")
async def broadcast(
    request: Request,
    req: BroadcastRequest,
    admin: dict = Depends(require_admin),
):
    """Send a system-wide broadcast notification."""
    notification = create_broadcast(req.title, req.content, req.target_group)

    log_activity(admin["id"], "admin_broadcast", {
        "target_group": req.target_group,
        "title": req.title,
    })
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="broadcast",
        target_user_id=None,
        details=f"Broadcast to {req.target_group}: {req.title[:50]}",
        reason=None,
    )

    return notification


@router.post("/send")
@limiter.limit("30/minute")
async def send_notification(
    request: Request,
    req: SendNotificationRequest,
    admin: dict = Depends(require_admin),
):
    """Send a notification to a single user."""
    notification = send_notification_to_user(
        user_id=req.user_id,
        title=req.title,
        content=req.content,
        notification_type=req.notification_type,
    )

    if not notification:
        raise HTTPException(500, "Failed to send notification")

    log_activity(admin["id"], "admin_notification_send", {
        "target_user": req.user_id,
        "title": req.title,
    })

    admin_log_operation(
        admin_id=admin["id"],
        operation_type="notification_send",
        target_user_id=req.user_id,
        details=f"Notification: {req.title[:50]}",
        reason=None,
    )

    return {"status": "sent", "notification": notification}


@router.post("/batch")
@limiter.limit("10/minute")
async def batch_notification(
    request: Request,
    req: BatchNotificationRequest,
    admin: dict = Depends(require_admin),
):
    """Send notifications to multiple users."""
    notifications = send_notification_to_users(
        user_ids=req.user_ids,
        title=req.title,
        content=req.content,
        notification_type=req.notification_type,
    )

    log_activity(admin["id"], "admin_notification_batch", {
        "user_count": len(req.user_ids),
        "title": req.title,
    })

    admin_log_operation(
        admin_id=admin["id"],
        operation_type="notification_batch",
        target_user_id=None,
        details=f"Batch notification to {len(req.user_ids)} users: {req.title[:50]}",
        reason=None,
    )

    return {"status": "sent", "count": len(notifications)}


@router.get("/stats")
async def get_notification_stats(
    admin: dict = Depends(require_admin),
):
    """Fetch notification statistics."""
    return get_all_notification_stats()


@router.get("/history")
async def get_notification_history_api(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    admin: dict = Depends(require_admin),
):
    """Fetch notification history."""
    return get_notification_history(page=page, limit=limit)
