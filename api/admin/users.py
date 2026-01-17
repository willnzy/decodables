"""
Admin Users API - User management endpoints for admins.

@module api.admin.users
@version 3.29 (API Consistency)

Changes in v3.29:
- Renamed query parameter 'query' to 'search' for API consistency
- Renamed path parameter 'uid' to 'user_id' for API consistency

Changes in v3.28:
- USER-ARCH-1: Migrated to Container-based dependency injection
- USER-ARCH-2: Created AdminUsersService for business logic
- USER-ARCH-3: Removed direct repository imports from API layer
- Architecture: API → Container → Service → Repository (Strict DIP)

Changes in v3.25:
- USER-MEDIUM-1: Added rate limiting to all 13 endpoints
- USER-MEDIUM-2: Migrated from page to offset pagination
- USER-MEDIUM-3: Added tier enum validation
- USER-LOW-1: Added field length limits to request models
- USER-LOW-2: Added user_id/project_id length validation
- USER-LOW-3: Limited error exposure

Endpoints:
- GET /users?search= - Search users
- GET /users/{user_id} - Get user audit
- POST /users/{user_id}/credits - Adjust credits
- PATCH /users/{user_id} - Update tier
- POST /users/{user_id}/discount - Create discount
- GET /users/{user_id}/payments - Get payment history
- GET /users/by-tier/{tier} - Get users by tier
- GET /users/{user_id}/projects - Get user projects
- GET /users/{user_id}/asset-usage - Get asset usage
- GET /users/{user_id}/env-stats - Get env stats
- POST /projects/{project_id}/restore - Restore deleted project
- GET /projects/feed - Site-wide project feed
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from dependencies import require_admin
from infrastructure.rate_limiter import limiter

# v3.28: Container-based DI
# WHY: API layer should not know about concrete repository implementations
from container import get_container

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin-users-v2"])


# ==========================================
# Dependency Injection (v3.28: Container-based)
# ==========================================

async def get_admin_users_service():
    """
    Get AdminUsersService from Container.

    WHY Container-based DI?
    1. Decouples API layer from infrastructure implementations
    2. Enables easy testing with mock services
    3. Centralizes dependency management
    4. Supports future provider switches
    """
    container = get_container()
    return await container.get_admin_users_service()


# ==========================================
# Request Models (v3.25: Added field validation)
# ==========================================

class CreditAdjustRequest(BaseModel):
    """Credit adjustment request."""
    amount: int
    bucket: str = Field("permanent", pattern="^(monthly|permanent)$")
    reason: Optional[str] = Field(None, max_length=500)


class TierUpdateRequest(BaseModel):
    """Tier update request."""
    tier: str = Field(..., pattern="^(t1|t2|t3|free|starter|pro)$")


class DiscountRequest(BaseModel):
    """Discount creation request."""
    discount_percent: int = Field(..., ge=1, le=100)
    valid_days: int = Field(7, ge=1, le=365)
    target_plan: Optional[str] = Field(None, max_length=50)


# ==========================================
# User Management Endpoints
# ==========================================

@router.get("/users")
@limiter.limit("30/minute")
async def search_users_api(
    request: Request,
    search: str = Query(..., min_length=1, max_length=200, description="Search by user_id, email, or user_code"),
    limit: int = Query(20, ge=1, le=100),
    admin: dict = Depends(require_admin),
    service = Depends(get_admin_users_service),
):
    """
    Search users by search string (user_id, email, or user_code).

    v3.28: Refactored to use AdminUsersService via Container.
    v3.29: Renamed parameter from 'query' to 'search' for API consistency.
    """
    return await service.search_users(search, limit=limit)


@router.get("/users/by-tier/{tier}")
@limiter.limit("30/minute")
async def get_users_by_tier_api(
    request: Request,
    tier: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    admin: dict = Depends(require_admin),
    service = Depends(get_admin_users_service),
):
    """
    Get users by tier with pagination.

    v3.28: Refactored to use AdminUsersService via Container.
    """
    try:
        return await service.get_users_by_tier(tier, offset=offset, limit=limit)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/users/{user_id}")
@limiter.limit("30/minute")
async def get_user_audit(
    request: Request,
    user_id: str,
    admin: dict = Depends(require_admin),
    service = Depends(get_admin_users_service),
):
    """Get full user audit data."""
    if len(user_id) > 100:
        raise HTTPException(400, "User ID too long (max 100 characters)")
    return await service.get_user_audit(user_id)


@router.post("/users/{user_id}/credits")
@limiter.limit("10/minute")
async def adjust_user_credits(
    request: Request,
    user_id: str,
    req: CreditAdjustRequest,
    admin: dict = Depends(require_admin),
    service = Depends(get_admin_users_service),
):
    """Manually adjust a user's credits with admin logging."""
    if len(user_id) > 100:
        raise HTTPException(400, "User ID too long (max 100 characters)")
    return await service.adjust_credits(user_id, req.amount, req.bucket, req.reason, admin["id"])


@router.patch("/users/{user_id}")
@limiter.limit("10/minute")
async def update_user(
    request: Request,
    user_id: str,
    req: TierUpdateRequest,
    admin: dict = Depends(require_admin),
    service = Depends(get_admin_users_service),
):
    """
    Update user properties (tier).

    v3.28: Refactored to use AdminUsersService via Container.
    v3.29: Renamed path parameter from 'uid' to 'user_id' for API consistency.
    """
    if len(user_id) > 100:
        raise HTTPException(400, "User ID too long (max 100 characters)")
    return await service.update_user_tier(user_id, req.tier, admin["id"])


@router.post("/users/{user_id}/tier", deprecated=True)
@limiter.limit("10/minute")
async def update_user_tier(
    request: Request,
    user_id: str,
    req: TierUpdateRequest,
    admin: dict = Depends(require_admin),
):
    """
    Update user tier (DEPRECATED - REMOVED in v3.26).

    **Please use `PATCH /users/{user_id}` instead.**
    """
    raise HTTPException(
        status_code=410,
        detail={
            "error": "Endpoint removed",
            "message": "POST /users/{user_id}/tier has been removed. Please use PATCH /users/{user_id} instead.",
            "replacement_endpoint": f"PATCH /admin/users/{user_id}",
        }
    )


@router.post("/users/{user_id}/discount")
@limiter.limit("10/minute")
async def create_user_discount_api(
    request: Request,
    user_id: str,
    req: DiscountRequest,
    admin: dict = Depends(require_admin),
    service = Depends(get_admin_users_service),
):
    """Create a user-specific discount with admin logging."""
    if len(user_id) > 100:
        raise HTTPException(400, "User ID too long (max 100 characters)")
    return await service.create_user_discount(
        user_id, req.discount_percent, req.valid_days, req.target_plan, admin["id"]
    )


@router.get("/users/{user_id}/payments")
@limiter.limit("30/minute")
async def get_user_payments(
    request: Request,
    user_id: str,
    admin: dict = Depends(require_admin),
    service = Depends(get_admin_users_service),
):
    """Fetch a user's payment history."""
    if len(user_id) > 100:
        raise HTTPException(400, "User ID too long (max 100 characters)")
    try:
        return await service.get_user_payments(user_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))


@router.get("/users/{user_id}/projects")
@limiter.limit("30/minute")
async def get_user_projects(
    request: Request,
    user_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    include_deleted: bool = True,
    admin: dict = Depends(require_admin),
    service = Depends(get_admin_users_service),
):
    """Fetch all projects owned by a specific user."""
    if len(user_id) > 100:
        raise HTTPException(400, "User ID too long (max 100 characters)")
    return await service.get_user_projects(user_id, offset, limit, include_deleted)


@router.get("/users/{user_id}/asset-usage")
@limiter.limit("30/minute")
async def get_user_asset_usage(
    request: Request,
    user_id: str,
    top_n: int = 10,
    admin: dict = Depends(require_admin),
    service = Depends(get_admin_users_service),
):
    """Get detailed asset usage for a user."""
    if len(user_id) > 100:
        raise HTTPException(400, "User ID too long (max 100 characters)")
    try:
        return await service.get_user_asset_usage(user_id, top_n=top_n)
    except Exception as e:
        logger.error(f"[Admin] Failed to get asset usage for {user_id}: {e}")
        raise HTTPException(500, "Failed to retrieve asset usage data")


@router.get("/users/{user_id}/env-stats")
@limiter.limit("30/minute")
async def get_user_env_stats(
    request: Request,
    user_id: str,
    limit: int = 100,
    admin: dict = Depends(require_admin),
    service = Depends(get_admin_users_service),
):
    """Get detailed user environment statistics."""
    if len(user_id) > 100:
        raise HTTPException(400, "User ID too long (max 100 characters)")
    try:
        return await service.get_user_env_stats(user_id, limit=limit)
    except Exception as e:
        logger.error(f"[Admin] Failed to get env stats for {user_id}: {e}")
        raise HTTPException(500, "Failed to retrieve environment statistics")


# ==========================================
# Project Management
# ==========================================

@router.post("/projects/{project_id}/restore")
@limiter.limit("10/minute")
async def restore_project_api(
    request: Request,
    project_id: str,
    admin: dict = Depends(require_admin),
    service = Depends(get_admin_users_service),
):
    """Restore a deleted project."""
    if len(project_id) > 100:
        raise HTTPException(400, "Project ID too long (max 100 characters)")
    project = await service.restore_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.get("/projects/feed")
@limiter.limit("30/minute")
async def get_projects_feed(
    request: Request,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin: dict = Depends(require_admin),
    service = Depends(get_admin_users_service),
):
    """Fetch the site-wide project feed."""
    return await service.get_projects_feed(offset, limit)
