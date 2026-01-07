"""
User API - User profile and account endpoints.

@module api.user_api
@version 1.0.0

Endpoints compatible with legacy /api/user/* for migration.

Endpoints:
- GET /api/v2/user/me - Get current user (compatible with /api/user/me)
- GET /api/v2/user/profile - Get user profile
- PUT /api/v2/user/timezone - Update timezone
"""

import logging
from typing import Optional, Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from dependencies import get_current_user
from container import get_container

from application.queries.billing import GetUserCreditsQuery
from application.queries.identity import GetUserProfileQuery

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/user", tags=["user-v2"])


# ==========================================
# Request/Response Models
# ==========================================

class UserMeResponse(BaseModel):
    """
    Response for /me endpoint.
    Compatible with legacy /api/user/me response.
    """
    id: str
    email: Optional[str] = None
    tier: str = "free"
    role: str = "user"
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: Optional[str] = None
    created_at: Optional[str] = None

    # Credits (compatible with legacy)
    credits_monthly: int = 0
    credits_permanent: int = 0
    credits_total: int = 0

    # Computed
    is_member: bool = False

    class Config:
        extra = "allow"  # Allow extra fields for compatibility


class TimezoneUpdateRequest(BaseModel):
    """Request to update timezone."""
    timezone: str


class TimezoneUpdateResponse(BaseModel):
    """Response for timezone update."""
    status: str
    timezone: str


# ==========================================
# Endpoints
# ==========================================

@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get current user info.

    Compatible with legacy /api/user/me response format.
    Returns full user profile with credits.
    """
    container = get_container()
    user_id = user["id"]

    # Get credits
    credits_handler = container.get_user_credits_handler
    credits_query = GetUserCreditsQuery(user_id=user_id)
    credits_result = await credits_handler.handle(credits_query)

    # Get profile
    profile_handler = container.get_user_profile_handler
    profile_query = GetUserProfileQuery(user_id=user_id)
    profile_result = await profile_handler.handle(profile_query)

    # Build response (compatible with legacy format)
    tier = "free"
    if credits_result.success:
        tier = credits_result.tier or "free"
    elif profile_result.success and profile_result.user:
        tier = profile_result.user.tier.value if hasattr(profile_result.user.tier, 'value') else str(profile_result.user.tier)

    tier_lower = tier.lower()
    is_member = tier_lower in ["starter", "pro"]

    # Start with user dict from auth
    response = {
        "id": user_id,
        "email": user.get("email"),
        "tier": tier,
        "role": user.get("role", "user"),
        "is_member": is_member,
    }

    # Add profile data if available
    if profile_result.success and profile_result.user_dict:
        profile_data = profile_result.user_dict
        response.update({
            "display_name": profile_data.get("display_name"),
            "avatar_url": profile_data.get("avatar_url"),
            "timezone": profile_data.get("timezone"),
            "created_at": profile_data.get("created_at"),
        })

    # Add credits (legacy field names)
    if credits_result.success:
        response.update({
            "credits_monthly": credits_result.monthly_credits,
            "credits_permanent": credits_result.permanent_credits,
            "credits_total": credits_result.total_credits,
        })
    else:
        response.update({
            "credits_monthly": 0,
            "credits_permanent": 0,
            "credits_total": 0,
        })

    return response


@router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get user profile (without credits).

    Lighter endpoint for profile-only data.
    """
    container = get_container()

    profile_handler = container.get_user_profile_handler
    query = GetUserProfileQuery(user_id=user["id"])
    result = await profile_handler.handle(query)

    if not result.success:
        # Return basic info from auth if profile not found
        return {
            "id": user["id"],
            "email": user.get("email"),
            "tier": user.get("tier", "free"),
            "role": user.get("role", "user"),
        }

    return result.user_dict


@router.put("/timezone", response_model=TimezoneUpdateResponse)
async def update_timezone(
    req: TimezoneUpdateRequest,
    user: dict = Depends(get_current_user),
):
    """
    Update user's timezone preference.

    Compatible with legacy /api/user/timezone.
    """
    from pytz import timezone as pytz_timezone
    from pytz.exceptions import UnknownTimeZoneError

    # Validate timezone
    try:
        pytz_timezone(req.timezone)
    except UnknownTimeZoneError:
        raise HTTPException(400, f"Invalid timezone: {req.timezone}")

    container = get_container()
    identity_service = container.identity_service

    try:
        # Update via service
        result = await identity_service.update_timezone(user["id"], req.timezone)

        if not result.success:
            raise HTTPException(500, "Failed to update timezone")

        return TimezoneUpdateResponse(
            status="ok",
            timezone=req.timezone,
        )
    except Exception as e:
        logger.error(f"Failed to update timezone for user {user['id']}: {e}")
        raise HTTPException(500, "Failed to update timezone")
