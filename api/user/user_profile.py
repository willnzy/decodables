"""
User Profile API - User profile and account endpoints (v2).

@module api.user.user_profile
@version 2.0.0

Endpoints:
- GET /api/v2/user/profile/me - Get current user
- GET /api/v2/user/profile/history - Get credit history
- GET /api/v2/user/profile/purchases - Get purchases
- GET /api/v2/user/profile/notifications - Get notifications
- POST /api/v2/user/profile/notifications/{id}/read - Mark notification read
- POST /api/v2/user/profile/notifications/read-all - Mark all read
- PUT /api/v2/user/profile/timezone - Update timezone
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

from infrastructure.repositories import (
    SupabaseUserRepositoryExtended,
    SupabaseCreditRepositoryExtended,
    SupabaseListingRepository,
    SupabaseNotificationRepositoryExtended,
)
from core.database import get_database_client
from dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["user-profile-v2"])


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
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user info (PRD v3.2)."""
    user_id = user["id"]

    db = get_database_client()
    user_repo = SupabaseUserRepositoryExtended(db)
    credit_repo = SupabaseCreditRepositoryExtended(db)

    # Reset monthly credits when needed
    await credit_repo.check_and_reset_monthly_credits_if_needed(user_id)

    user_profile = await user_repo.get_profile(user_id)
    if not user_profile:
        user_profile = user

    return {
        **user_profile,
        "credits_total": user_profile.get("credits_monthly", 0) + user_profile.get("credits_permanent", 0),
        "is_member": is_member(user_profile)
    }


@router.get("/history")
async def get_history(
    page: int = 1,
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    """Get credit history."""
    db = get_database_client()
    credit_repo = SupabaseCreditRepositoryExtended(db)
    result = await credit_repo.get_credit_history(user["id"], page, limit)
    return {"items": result["items"], "total": result["total"], "page": page}


@router.get("/purchases")
async def get_purchases(user: dict = Depends(get_current_user)):
    """Get user's marketplace purchases."""
    db = get_database_client()
    listing_repo = SupabaseListingRepository(db)
    return await listing_repo.get_user_purchases(user["id"])


@router.get("/notifications")
async def get_notifications(user: dict = Depends(get_current_user)):
    """Get user notifications."""
    db = get_database_client()
    notif_repo = SupabaseNotificationRepositoryExtended(db)
    return await notif_repo.get_user_notifications(user["id"])


@router.post("/notifications/{id}/read")
async def mark_read(id: str, user: dict = Depends(get_current_user)):
    """Mark a notification as read."""
    db = get_database_client()
    notif_repo = SupabaseNotificationRepositoryExtended(db)
    result = await notif_repo.mark_notification_read(id, user["id"])
    if not result:
        raise HTTPException(404, "Notification not found")
    return {"status": "ok"}


@router.post("/notifications/read-all")
async def mark_all_read(user: dict = Depends(get_current_user)):
    """Mark all notifications as read."""
    db = get_database_client()
    notif_repo = SupabaseNotificationRepositoryExtended(db)
    await notif_repo.mark_all_notifications_read(user["id"])
    return {"status": "ok"}


@router.put("/timezone")
async def update_timezone(
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

    db = get_database_client()
    user_repo = SupabaseUserRepositoryExtended(db)
    result = await user_repo.update_timezone(user["id"], req.timezone)
    if not result:
        raise HTTPException(500, "Failed to update timezone")

    return {"status": "ok", "timezone": req.timezone}
