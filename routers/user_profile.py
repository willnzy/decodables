"""
User Profile Router - User profile and account endpoints

@module routers.user_profile
@version 3.24

Endpoints:
- GET /api/user/me - Get current user
- GET /api/user/history - Get credit history
- GET /api/user/purchases - Get purchases
- GET /api/user/notifications - Get notifications
- POST /api/user/notifications/{id}/read - Mark notification read
- POST /api/user/notifications/read-all - Mark all read
- PUT /api/user/timezone - Update timezone
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

from services.db_service import (
    get_credit_history,
    get_user_purchases,
    get_user_notifications,
    mark_notification_read,
    mark_all_notifications_read,
    update_user_timezone,
    get_user_profile,
    check_and_reset_monthly_credits_if_needed,
)
from dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user", tags=["user-profile"])


# ==========================================
# Request Models
# ==========================================

class TimezoneUpdateRequest(BaseModel):
    timezone: str


# ==========================================
# Helper Functions
# ==========================================

def is_member(user: dict) -> bool:
    """Check if user is a paying member."""
    tier = (user.get("tier") or "free").lower()
    return tier in ["starter", "pro"]


# ==========================================
# Profile Endpoints
# ==========================================

@router.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    """Get current user info (PRD v3.2)."""
    user_id = user["id"]
    
    # Reset monthly credits when needed
    check_and_reset_monthly_credits_if_needed(user_id)
    
    user_profile = get_user_profile(user_id)
    if not user_profile:
        user_profile = user
    
    return {
        **user_profile,
        "credits_total": user_profile.get("credits_monthly", 0) + user_profile.get("credits_permanent", 0),
        "is_member": is_member(user_profile)
    }


@router.get("/history")
def get_history(
    page: int = 1, 
    limit: int = 20, 
    user: dict = Depends(get_current_user)
):
    """Get credit history."""
    result = get_credit_history(user["id"], page, limit)
    return {"items": result["items"], "total": result["total"], "page": page}


@router.get("/purchases")
def get_purchases(user: dict = Depends(get_current_user)):
    """Get user's marketplace purchases."""
    return get_user_purchases(user["id"])


@router.get("/notifications")
def get_notifications(user: dict = Depends(get_current_user)):
    """Get user notifications."""
    return get_user_notifications(user["id"])


@router.post("/notifications/{id}/read")
def mark_read(id: str, user: dict = Depends(get_current_user)):
    """Mark a notification as read."""
    result = mark_notification_read(id, user["id"])
    if not result:
        raise HTTPException(404, "Notification not found")
    return {"status": "ok"}


@router.post("/notifications/read-all")
def mark_all_read(user: dict = Depends(get_current_user)):
    """Mark all notifications as read."""
    mark_all_notifications_read(user["id"])
    return {"status": "ok"}


@router.put("/timezone")
def update_timezone(
    request: Request,
    req: TimezoneUpdateRequest, 
    user: dict = Depends(get_current_user)
):
    """Update user's timezone preference."""
    from pytz import timezone as pytz_timezone
    from pytz.exceptions import UnknownTimeZoneError
    
    try:
        pytz_timezone(req.timezone)
    except UnknownTimeZoneError:
        raise HTTPException(400, f"Invalid timezone: {req.timezone}")
    
    result = update_user_timezone(user["id"], req.timezone)
    if not result:
        raise HTTPException(500, "Failed to update timezone")
    
    return {"status": "ok", "timezone": req.timezone}
