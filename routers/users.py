"""
Users Router
Handles user-related API endpoints

@module routers/users
"""

from fastapi import APIRouter, Depends
from dependencies import get_current_user
from db_service import (
    get_user_profile, get_credit_history, get_assets,
    get_user_purchases, get_user_notifications, mark_notification_read
)

router = APIRouter(prefix="/api/user", tags=["users"])


@router.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    """
    Get current user info.
    
    Returns:
        User profile with credits breakdown and tier info
    """
    return {
        "id": user["id"],
        "email": user.get("email"),
        "username": user.get("username"),
        "avatar_url": user.get("avatar_url"),
        "tier": user.get("tier", "free"),
        "subscription_status": user.get("subscription_status", "inactive"),
        "credits_monthly": user.get("credits_monthly", 0),
        "credits_permanent": user.get("credits_permanent", 0),
        "credits_total": user.get("credits_monthly", 0) + user.get("credits_permanent", 0),
        "is_member": user.get("tier") in ["starter", "pro"] and user.get("subscription_status") == "active",
        "role": user.get("role", "user"),
    }


@router.get("/history")
def get_history(page: int = 1, limit: int = 20, user: dict = Depends(get_current_user)):
    """
    Get credit transaction history.
    
    Args:
        page: Page number
        limit: Items per page
    
    Returns:
        Credit history with pagination
    """
    items = get_credit_history(user["id"], page, limit)
    return {"items": items, "total": len(items), "page": page}


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

