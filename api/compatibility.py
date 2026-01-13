"""
Backward Compatibility API - Routes for legacy frontend paths.

@module api.compatibility
@version 1.0.0

This module provides backward compatibility for old API paths that were
deprecated during the v2 migration. These routes redirect to the new v2 endpoints.

Legacy paths supported:
- /api/user/* → /api/v2/user/profile/*

NOTE: These routes should be removed once the frontend is fully migrated to v2 paths.
"""

from fastapi import APIRouter, Request, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user
from domains.identity.user_profile_service import UserProfileService
from api.user.user_profile import get_user_profile_service

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api/user", tags=["compatibility-v1"])


@router.get("/notifications")
@limiter.limit("50/minute")
async def get_notifications_v1_compat(
    request: Request,
    unread_only: bool = False,
    user: dict = Depends(get_current_user),
    profile_service: UserProfileService = Depends(get_user_profile_service),
):
    """
    [DEPRECATED] Backward compatibility endpoint for /api/user/notifications.

    Frontend should migrate to: /api/v2/user/profile/notifications

    Args:
        unread_only: If True, return only unread notifications
    """
    return await profile_service.get_notifications(user["id"], unread_only=unread_only)


@router.post("/notifications/{id}/read")
@limiter.limit("30/minute")
async def mark_notification_read_v1_compat(
    request: Request,
    id: str,
    user: dict = Depends(get_current_user),
    profile_service: UserProfileService = Depends(get_user_profile_service),
):
    """
    [DEPRECATED] Backward compatibility endpoint for marking notification as read.

    Frontend should migrate to: /api/v2/user/profile/notifications/{id}/read
    """
    success = await profile_service.mark_notification_read(id, user["id"])
    return {"success": success}


@router.post("/notifications/read-all")
@limiter.limit("20/minute")
async def mark_all_notifications_read_v1_compat(
    request: Request,
    user: dict = Depends(get_current_user),
    profile_service: UserProfileService = Depends(get_user_profile_service),
):
    """
    [DEPRECATED] Backward compatibility endpoint for marking all notifications as read.

    Frontend should migrate to: /api/v2/user/profile/notifications/read-all
    """
    await profile_service.mark_all_notifications_read(user["id"])
    return {"success": True}
