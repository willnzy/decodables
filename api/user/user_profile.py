"""
User Profile API - User profile and account endpoints (v2).

@module api.user.user_profile
@version 2.3.0 (Container-based DI)

Changes in v2.3.0:
- UP-ARCH-1: Migrated to Container-based dependency injection
- UP-ARCH-2: Removed direct infrastructure imports in API layer
- UP-ARCH-3: API layer now only depends on Container, not repositories
- Architecture: API → Container → Service → Repository (Strict DIP)

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

from domains.identity.aggregates.user_profile import UserProfile
from domains.identity.user_profile_service import UserProfileService
from infrastructure.rate_limiter import limiter
from dependencies import get_current_user

# v2.3.0: Import Container instead of individual repositories
# WHY: Dependency Inversion Principle (DIP) - API layer should not know about
# concrete repository implementations. Container handles all wiring.
from container import get_container, Container

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["user-profile-v2"])


# ==========================================
# Dependency Injection (v2.3.0: Container-based)
# ==========================================

async def get_user_profile_service() -> UserProfileService:
    """
    Dependency injection factory for UserProfileService.

    v2.3.0: Uses Container pattern instead of direct repository instantiation.

    WHY Container-based DI?
    1. Decouples API layer from infrastructure implementations
    2. Enables easy testing with mock services
    3. Centralizes dependency management
    4. Supports future provider switches (Supabase -> other DB)

    Returns:
        UserProfileService instance from Container
    """
    container = get_container()
    return await container.get_user_profile_service()


# ==========================================
# Request Models
# ==========================================

class UserProfileResponse(BaseModel):
    """Response model for /me endpoint."""
    user_id: str
    user_code: str = ""
    email: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    tier: str = "t1"
    role: str = "user"
    credits_monthly: int = 0
    credits_permanent: int = 0
    credits_total: int = 0
    subscription_status: Optional[str] = None
    subscription_end_date: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    timezone: Optional[str] = None
    is_member: bool = False
    is_within_trial: bool = False


class TimezoneUpdateRequest(BaseModel):
    timezone: str


# ==========================================
# Profile Endpoints
# ==========================================

@router.get("/me")
@limiter.limit("100/minute")  # v2.2.0: Added rate limiting
async def get_me(
    request: Request,
    user: UserProfile = Depends(get_current_user),
    profile_service: UserProfileService = Depends(get_user_profile_service),  # v2.2.0: DI
) -> UserProfileResponse:
    """Get current user info (PRD v3.2)."""
    profile = await profile_service.get_user_profile(user.user_id)
    if not profile:
        # Fallback to basic user data from the UserProfile dataclass
        # Build display name from user fields
        first_name = user.first_name or ""
        last_name = user.last_name or ""
        name = f"{first_name} {last_name}".strip() or user.display_name or user.username

        profile = {
            "user_id": user.user_id,
            "user_code": user.user_code or "",
            "email": user.email,
            "name": name if name else None,
            "avatar_url": user.avatar_url,
            "tier": user.tier.value if hasattr(user.tier, 'value') else str(user.tier),
            "credits_monthly": 0,
            "credits_permanent": 0,
            "credits_total": 0,
            "subscription_status": user.subscription_status,
            "subscription_end_date": None,
            "created_at": user.created_at.isoformat() if user.created_at else "",
            "updated_at": user.updated_at.isoformat() if user.updated_at else "",
            "timezone": None,
            "is_member": False,
            "is_within_trial": False,
        }
    return UserProfileResponse(**profile)


@router.get("/history")
@limiter.limit("50/minute")  # v2.2.0: Added rate limiting
async def get_history(
    request: Request,
    offset: int = 0,  # v2.1.0: UP-P0-3 fix - use offset/limit per DDD standards
    limit: int = 20,
    user: UserProfile = Depends(get_current_user),
    profile_service: UserProfileService = Depends(get_user_profile_service),  # v2.2.0: DI
):
    """Get credit history."""
    return await profile_service.get_credit_history(user.user_id, offset, limit)


@router.get("/purchases")
@limiter.limit("50/minute")  # v2.2.0: Added rate limiting
async def get_purchases(
    request: Request,
    user: UserProfile = Depends(get_current_user),
    profile_service: UserProfileService = Depends(get_user_profile_service),  # v2.2.0: DI
):
    """Get user's marketplace purchases."""
    return await profile_service.get_purchases(user.user_id)


@router.get("/notifications")
@limiter.limit("50/minute")  # v2.2.0: Added rate limiting
async def get_notifications(
    request: Request,
    unread_only: bool = False,
    user: UserProfile = Depends(get_current_user),
    profile_service: UserProfileService = Depends(get_user_profile_service),  # v2.2.0: DI
):
    """
    Get user notifications.

    Args:
        unread_only: If True, return only unread notifications
    """
    return await profile_service.get_notifications(user.user_id, unread_only=unread_only)


@router.post("/notifications/{id}/read")
@limiter.limit("30/minute")  # v2.2.0: Added rate limiting
async def mark_read(
    request: Request,
    id: str,
    user: UserProfile = Depends(get_current_user),
    profile_service: UserProfileService = Depends(get_user_profile_service),  # v2.2.0: DI
):
    """Mark a notification as read."""
    success = await profile_service.mark_notification_read(id, user.user_id)
    if not success:
        raise HTTPException(404, "Notification not found")
    return {"status": "ok"}


@router.post("/notifications/read-all")
@limiter.limit("20/minute")  # v2.2.0: Added rate limiting
async def mark_all_read(
    request: Request,
    user: UserProfile = Depends(get_current_user),
    profile_service: UserProfileService = Depends(get_user_profile_service),  # v2.2.0: DI
):
    """Mark all notifications as read."""
    await profile_service.mark_all_notifications_read(user.user_id)
    return {"status": "ok"}


@router.put("/timezone")
@limiter.limit("20/minute")  # v2.2.0: Added rate limiting
async def update_timezone(
    request: Request,
    req: TimezoneUpdateRequest,
    user: UserProfile = Depends(get_current_user),
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
    success = await profile_service.update_timezone(user.user_id, req.timezone)
    if not success:
        raise HTTPException(500, "Failed to update timezone")

    return {"status": "ok", "timezone": req.timezone}
