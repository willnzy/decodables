"""
Users Router
Handles user-related API endpoints

@module routers/users
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional
from dependencies import get_current_user
from services.db_service import (
    get_user_profile, get_credit_history, get_assets,
    get_user_purchases, get_user_notifications, mark_notification_read,
    check_and_reset_monthly_credits_if_needed, update_user_timezone
)


class TimezoneUpdateRequest(BaseModel):
    """Request body for updating user timezone."""
    timezone: str = Field(..., min_length=1, max_length=50, description="IANA timezone identifier (e.g., 'Asia/Shanghai')")

router = APIRouter(prefix="/api/user", tags=["users"])


@router.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    """
    Get current user info (PRD v3.2).
    
    Important: Checks and resets monthly credits if needed (monthly reset logic)
    - Monthly credits reset every 30 days for Starter/Pro users
    - Permanent credits are never reset
    
    Returns:
        User profile with credits breakdown, tier info, and created_at for Free trial check
    """
    user_id = user["id"]
    
    #  monthly credits（）
    #  Stripe webhook ，monthly credits 
    # permanent credits 
    check_and_reset_monthly_credits_if_needed(user_id)
    
    # （）
    user_profile = get_user_profile(user_id)
    if not user_profile:
        # Fallback to user dict if profile not found
        user_profile = user
    
    return {
        "id": user_profile.get("id", user["id"]),
        "email": user_profile.get("email", user.get("email")),
        "username": user_profile.get("username", user.get("username")),
        "avatar_url": user_profile.get("avatar_url", user.get("avatar_url")),
        "created_at": user_profile.get("created_at", user.get("created_at")),  # For Free 7-day trial check
        "tier": user_profile.get("tier", user.get("tier", "free")),
        "subscription_status": user_profile.get("subscription_status", user.get("subscription_status", "inactive")),
        "credits_monthly": user_profile.get("credits_monthly", user.get("credits_monthly", 0)),
        "credits_permanent": user_profile.get("credits_permanent", user.get("credits_permanent", 0)),
        "credits_total": user_profile.get("credits_monthly", user.get("credits_monthly", 0)) + user_profile.get("credits_permanent", user.get("credits_permanent", 0)),
        "is_member": user_profile.get("tier", user.get("tier", "free")) in ["starter", "pro"] and user_profile.get("subscription_status", user.get("subscription_status", "inactive")) == "active",
        "role": user_profile.get("role", user.get("role", "user")),
    }


@router.get("/history")
def get_history(page: int = 1, limit: int = 20, user: dict = Depends(get_current_user)):
    """
    Get credit transaction history.
    
    Args:
        page: Page number
        limit: Items per page
    
    Returns:
        Credit history with pagination (items, total count, page)
    """
    result = get_credit_history(user["id"], page, limit)
    return {"items": result["items"], "total": result["total"], "page": page}


@router.get("/assets")
def get_user_assets(
    scope: str = "project",
    project_id: str = None,
    user: dict = Depends(get_current_user)
):
    """
    Get user's assets (uploaded images, AI generated).
    
    Args:
        scope: 'project' or 'all'
        project_id: Project ID when scope is 'project'
    
    Returns:
        List of assets
    """
    return get_assets(user["id"], project_id if scope == "project" else None)


@router.get("/purchases")
def get_purchases(page: int = 1, limit: int = 50, user: dict = Depends(get_current_user)):
    """
    Get user's marketplace purchases.
    
    Returns:
        Purchased items with pagination
    """
    items = get_user_purchases(user["id"], page, limit)
    return {"items": items, "total": len(items), "page": page}


@router.get("/notifications")
def get_notifications(unread_only: bool = False, user: dict = Depends(get_current_user)):
    """
    Get user's notifications.
    
    Args:
        unread_only: Filter to unread only
    
    Returns:
        List of notifications
    """
    return get_user_notifications(user["id"], unread_only)


@router.post("/notifications/{notification_id}/read")
def read_notification(notification_id: str, user: dict = Depends(get_current_user)):
    """
    Mark a notification as read.
    
    Returns:
        Updated notification
    """
    return mark_notification_read(notification_id, user["id"])


@router.post("/notifications/read-all")
def read_all_notifications(user: dict = Depends(get_current_user)):
    """
    Mark all notifications as read.
    
    Returns:
        Success message
    """
    from services.db_service import mark_all_notifications_read
    mark_all_notifications_read(user["id"])
    return {"success": True, "message": "All notifications marked as read"}


@router.put("/timezone")
def update_timezone(request: TimezoneUpdateRequest, user: dict = Depends(get_current_user)):
    """
    Update user's timezone.
    
    Called automatically when user logs in from browser to sync their timezone.
    Timezone is stored in IANA format (e.g., 'Asia/Shanghai', 'America/New_York').
    
    This enables the "dual storage" strategy:
    - UTC for all business logic and calculations
    - Local time (computed via trigger) for Admin panel display
    
    Args:
        request: TimezoneUpdateRequest with timezone field
    
    Returns:
        Success status and updated timezone
    """
    timezone = request.timezone
    
    # Basic validation for IANA timezone format
    if '/' not in timezone and timezone != 'UTC':
        return {"success": False, "error": "Invalid timezone format. Use IANA format like 'Asia/Shanghai'"}
    
    success = update_user_timezone(user["id"], timezone)
    
    return {
        "success": success,
        "timezone": timezone,
        "message": f"Timezone updated to {timezone}" if success else "Failed to update timezone"
    }

