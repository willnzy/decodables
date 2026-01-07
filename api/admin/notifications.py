"""
Admin Notifications Router - Notification management endpoints for admins

@module api.admin.notifications
@version 3.24

Endpoints:
- POST /api/admin/broadcast - Send broadcast notification
- POST /api/admin/notification/send - Send to single user
- POST /api/admin/notification/batch - Send to multiple users
- GET /api/admin/notification/stats - Get notification stats
- GET /api/admin/notification/history - Get notification history
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

from infrastructure.db_compat import (
    create_broadcast,
    send_notification_to_user,
    send_notification_to_users,
    get_all_notification_stats,
    get_notification_history,
    admin_log_operation,
    log_activity,
)
from infrastructure.rate_limiter import limiter
from dependencies import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["admin-notifications-v2"])


# ==========================================
# Request Models
# ==========================================

class AdminBroadcastRequest(BaseModel):
    title: str
    content: str
    target_group: Optional[str] = "all"  # 'all', 'free', 'starter', 'pro'


class AdminSendNotificationRequest(BaseModel):
    user_id: str
    title: str
    content: str
    notification_type: Optional[str] = "system"


class AdminBatchNotificationRequest(BaseModel):
    user_ids: List[str]
    title: str
    content: str
    notification_type: Optional[str] = "system"


# ==========================================
# Notification Endpoints
# ==========================================

@router.post("/broadcast")
@limiter.limit("5/minute")
def adm_broadcast(request: Request, req: AdminBroadcastRequest, admin: dict = Depends(require_admin)):
    """Send a system-wide broadcast notification."""
    notification = create_broadcast(req.title, req.content, req.target_group)
    log_activity(admin["id"], "admin_broadcast", {
        "target_group": req.target_group,
        "title": req.title
    })
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="broadcast",
        target_user_id=None,
        details=f"Broadcast to {req.target_group}: {req.title[:50]}",
        reason=None
    )
    return notification


@router.post("/notification/send")
@limiter.limit("30/minute")
def adm_send_notification(request: Request, req: AdminSendNotificationRequest, admin: dict = Depends(require_admin)):
    """Send a notification to a single user."""
    notification = send_notification_to_user(
        user_id=req.user_id,
        title=req.title,
        content=req.content,
        notification_type=req.notification_type
    )
    
    if not notification:
        raise HTTPException(500, "Failed to send notification")
    
    log_activity(admin["id"], "admin_notification_send", {
        "target_user": req.user_id,
        "title": req.title
    })
    
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="notification_send",
        target_user_id=req.user_id,
        details=f"Notification: {req.title[:50]}",
        reason=None
    )
    
    return {"status": "sent", "notification": notification}


@router.post("/notification/batch")
@limiter.limit("10/minute")
def adm_batch_notification(request: Request, req: AdminBatchNotificationRequest, admin: dict = Depends(require_admin)):
    """Send notifications to multiple users."""
    if len(req.user_ids) > 100:
        raise HTTPException(400, "Cannot send to more than 100 users at once")
    
    notifications = send_notification_to_users(
        user_ids=req.user_ids,
        title=req.title,
        content=req.content,
        notification_type=req.notification_type
    )
    
    log_activity(admin["id"], "admin_notification_batch", {
        "user_count": len(req.user_ids),
        "title": req.title
    })
    
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="notification_batch",
        target_user_id=None,
        details=f"Batch notification to {len(req.user_ids)} users: {req.title[:50]}",
        reason=None
    )
    
    return {"status": "sent", "count": len(notifications)}


@router.get("/notification/stats")
def adm_notification_stats(admin: dict = Depends(require_admin)):
    """Fetch notification statistics."""
    return get_all_notification_stats()


@router.get("/notification/history")
def adm_notification_history(
    page: int = 1,
    limit: int = 50,
    admin: dict = Depends(require_admin)
):
    """Fetch notification history."""
    return get_notification_history(page=page, limit=limit)
