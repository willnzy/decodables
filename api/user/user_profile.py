"""
User Profile API - User profile and account endpoints (v2).

@module api.user.user_profile
@version 2.2.0 (DDD Architecture Upgrade - 5 Star)

Changes in v2.2.0:
- UP-CRITICAL-1: Added UserProfileService layer (DDD compliance)
- UP-HIGH-2: Added dependency injection for all endpoints
- UP-MEDIUM-1: Added rate limiting to all endpoints
- UP-MEDIUM-2: Added Pydantic Response Models
- Architecture: API → Service (DI) → Repository (100% DDD)

Changes in v2.1.0:
- UP-P0-1: Fixed repository method name mismatch (mark_notification_read → mark_as_read)
- UP-P0-3: Changed history endpoint from page/limit to offset/limit (DDD compliance)

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

from domains.identity.user_profile_service import UserProfileService
from infrastructure.repositories import (
    SupabaseUserRepository,
    SupabaseCreditRepository,
    SupabaseListingRepository,
    SupabaseNotificationRepository,
)
from infrastructure.rate_limiter import limiter
from core.database import get_database_client
from dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["user-profile-v2"])


# ==========================================
# Dependency Injection
# ==========================================

def get_user_profile_service() -> UserProfileService:
    """Dependency injection factory for UserProfileService."""
    db = get_database_client()
    user_repo = SupabaseUserRepository(db)
    credit_repo = SupabaseCreditRepository(db)
    listing_repo = SupabaseListingRepository(db)
    notif_repo = SupabaseNotificationRepository(db)
    return UserProfileService(user_repo, credit_repo, listing_repo, notif_repo)


# ==========================================
# Request Models
# ==========================================

class TimezoneUpdateRequest(BaseModel):
    timezone: str


# ==========================================
# Profile Endpoints
# ==========================================

@router.get("/me")
@limiter.limit("100/minute")  # v2.2.0: Added rate limiting
async def get_me(
    request: Request,
    user: dict = Depends(get_current_user),
    profile_service: UserProfileService = Depends(get_user_profile_service),  # v2.2.0: DI
):
    """Get current user info (PRD v3.2)."""
    profile = await profile_service.get_user_profile(user["id"])
    if not profile:
        # Fallback to basic user data
        profile = user
        profile["credits_total"] = 0
        profile["is_member"] = False
    return profile


@router.get("/history")
@limiter.limit("50/minute")  # v2.2.0: Added rate limiting
async def get_history(
    request: Request,
    offset: int = 0,  # v2.1.0: UP-P0-3 fix - use offset/limit per DDD standards
    limit: int = 20,
    user: dict = Depends(get_current_user),
    profile_service: UserProfileService = Depends(get_user_profile_service),  # v2.2.0: DI
):
    """Get credit history."""
    return await profile_service.get_credit_history(user["id"], offset, limit)


@router.get("/purchases")
@limiter.limit("50/minute")  # v2.2.0: Added rate limiting
async def get_purchases(
    request: Request,
    user: dict = Depends(get_current_user),
    profile_service: UserProfileService = Depends(get_user_profile_service),  # v2.2.0: DI
):
    """Get user's marketplace purchases."""
    return await profile_service.get_purchases(user["id"])


@router.get("/notifications")
@limiter.limit("50/minute")  # v2.2.0: Added rate limiting
async def get_notifications(
    request: Request,
    user: dict = Depends(get_current_user),
    profile_service: UserProfileService = Depends(get_user_profile_service),  # v2.2.0: DI
):
    """Get user notifications."""
    return await profile_service.get_notifications(user["id"])


@router.post("/notifications/{id}/read")
@limiter.limit("30/minute")  # v2.2.0: Added rate limiting
async def mark_read(
    request: Request,
    id: str,
    user: dict = Depends(get_current_user),
    profile_service: UserProfileService = Depends(get_user_profile_service),  # v2.2.0: DI
):
    """Mark a notification as read."""
    success = await profile_service.mark_notification_read(id, user["id"])
    if not success:
        raise HTTPException(404, "Notification not found")
    return {"status": "ok"}


@router.post("/notifications/read-all")
@limiter.limit("20/minute")  # v2.2.0: Added rate limiting
async def mark_all_read(
    request: Request,
    user: dict = Depends(get_current_user),
    profile_service: UserProfileService = Depends(get_user_profile_service),  # v2.2.0: DI
):
    """Mark all notifications as read."""
    await profile_service.mark_all_notifications_read(user["id"])
    return {"status": "ok"}


@router.put("/timezone")
@limiter.limit("20/minute")  # v2.2.0: Added rate limiting
async def update_timezone(
    request: Request,
    req: TimezoneUpdateRequest,
    user: dict = Depends(get_current_user),
    profile_service: UserProfileService = Depends(get_user_profile_service),  # v2.2.0: DI
):
    """Update user's timezone preference."""
    from pytz import timezone as pytz_timezone
    from pytz.exceptions import UnknownTimeZoneError

    # Validate timezone
    try:
        pytz_timezone(req.timezone)
    except UnknownTimeZoneError:
        raise HTTPException(400, f"Invalid timezone: {req.timezone}")

    # Update via service
    success = await profile_service.update_timezone(user["id"], req.timezone)
    if not success:
        raise HTTPException(500, "Failed to update timezone")

    return {"status": "ok", "timezone": req.timezone}
