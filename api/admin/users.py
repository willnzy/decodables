"""
Admin Users API - User management endpoints for admins.

@module api.admin.users
@version 3.25

Changes:
- v3.25: Security improvements
  - USER-MEDIUM-1: Added rate limiting to all 13 endpoints
  - USER-MEDIUM-2: Migrated from page to offset pagination
  - USER-MEDIUM-3: Added tier enum validation
  - USER-LOW-1: Added field length limits to request models
  - USER-LOW-2: Added uid/project_id length validation
  - USER-LOW-3: Limited error exposure

Endpoints:
- GET /users - Search users
- GET /users/{uid} - Get user audit
- POST /users/{uid}/credits - Adjust credits
- POST /users/{uid}/tier - Update tier
- POST /users/{uid}/discount - Create discount
- GET /users/{uid}/payments - Get payment history
- GET /users/by-tier/{tier} - Get users by tier
- GET /users/{uid}/projects - Get user projects
- GET /users/{uid}/asset-usage - Get asset usage
- GET /users/{uid}/env-stats - Get env stats
- POST /projects/{project_id}/restore - Restore deleted project
- GET /projects/feed - Site-wide project feed
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from dependencies import require_admin
from core.database import get_supabase_client, get_database_client
from infrastructure.rate_limiter import limiter
from infrastructure.repositories import (
    SupabaseAdminUsersRepository,
    SupabaseCreditRepository,
    SupabaseProjectRepository,
    SupabaseUserRepository,
)
from domains.billing.payment_service import get_customer_payments

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin-users-v2"])


# ==========================================
# Constants (v3.25)
# ==========================================

# v3.25: USER-MEDIUM-3 - Valid user tiers
VALID_TIERS = {"free", "starter", "pro"}


# ==========================================
# Request Models (v3.25: Added field validation)
# ==========================================

class CreditAdjustRequest(BaseModel):
    """Credit adjustment request."""
    amount: int
    bucket: str = Field("permanent", pattern="^(monthly|permanent)$")
    # v3.25: USER-LOW-1 - Field length limits
    reason: Optional[str] = Field(None, max_length=500)


class TierUpdateRequest(BaseModel):
    """Tier update request."""
    tier: str = Field(..., pattern="^(free|starter|pro)$")


class DiscountRequest(BaseModel):
    """Discount creation request."""
    discount_percent: int = Field(..., ge=1, le=100)
    valid_days: int = Field(7, ge=1, le=365)
    # v3.25: USER-LOW-1 - Field length limits
    target_plan: Optional[str] = Field(None, max_length=50)


# ==========================================
# User Management Endpoints (v3.25: Added rate limiting and validation)
# ==========================================

@router.get("/users")
@limiter.limit("30/minute")
async def search_users_api(
    request: Request,
    query: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return (1-100)"),
    admin: dict = Depends(require_admin),
):
    """
    Search users by query.

    v3.26 (USER-MEDIUM-1): Added limit parameter to prevent large result sets
    """
    db = get_database_client()
    user_repo = SupabaseUserRepository(db)
    users = await user_repo.search_users(query, limit=limit)
    return {"users": users, "count": len(users), "limit": limit}


@router.get("/users/by-tier/{tier}")
@limiter.limit("30/minute")
async def get_users_by_tier_api(
    request: Request,
    tier: str,
    offset: int = 0,
    limit: int = 100,
    admin: dict = Depends(require_admin),
):
    """
    Get users by tier (for bulk notifications).

    v3.26 (REPO-HIGH-3): Added pagination (offset/limit) to prevent OOM
    """
    # v3.25: USER-MEDIUM-3 - Validate tier enum
    tier_lower = tier.lower()
    if tier_lower not in VALID_TIERS:
        raise HTTPException(400, f"Invalid tier. Must be one of: {', '.join(VALID_TIERS)}")

    db = get_database_client()
    user_repo = SupabaseUserRepository(db)
    # v3.26: Pass pagination parameters
    users = await user_repo.get_users_by_tier(tier_lower, offset=offset, limit=limit)
    return {
        "users": users,
        "count": len(users),
        "tier": tier_lower,
        "offset": offset,
        "limit": limit,
        "has_more": len(users) >= limit
    }


@router.get("/users/{uid}")
@limiter.limit("30/minute")
async def get_user_audit(
    request: Request,
    uid: str,
    admin: dict = Depends(require_admin),
):
    """Get full user audit data."""
    # v3.25: USER-LOW-2 - Validate uid length
    if len(uid) > 100:
        raise HTTPException(400, "User ID too long (max 100 characters)")

    db = get_database_client()
    admin_repo = SupabaseAdminUsersRepository(db)
    return await admin_repo.get_full_user_audit(uid)


@router.post("/users/{uid}/credits")
@limiter.limit("10/minute")
async def adjust_user_credits(
    request: Request,
    uid: str,
    req: CreditAdjustRequest,
    admin: dict = Depends(require_admin),
):
    """Manually adjust a user's credits."""
    # v3.25: USER-LOW-2 - Validate uid length
    if len(uid) > 100:
        raise HTTPException(400, "User ID too long (max 100 characters)")

    db = get_database_client()
    admin_repo = SupabaseAdminUsersRepository(db)

    await admin_repo.admin_adjust_credits(uid, req.amount, req.bucket, req.reason)
    await admin_repo.admin_log_operation(
        admin_id=admin["id"],
        operation_type="credit_adjust",
        target_user_id=uid,
        details=f"{'+' if req.amount > 0 else ''}{req.amount} {req.bucket} credits",
        reason=req.reason,
    )
    return {"status": "ok"}


@router.patch("/users/{uid}")
@limiter.limit("10/minute")
async def update_user(
    request: Request,
    uid: str,
    req: TierUpdateRequest,
    admin: dict = Depends(require_admin),
):
    """
    Update user properties (tier, etc.).

    **Recommended**: Use PATCH for partial resource updates.
    """
    # v3.25: USER-LOW-2 - Validate uid length
    if len(uid) > 100:
        raise HTTPException(400, "User ID too long (max 100 characters)")

    db = get_database_client()
    user_repo = SupabaseUserRepository(db)
    admin_repo = SupabaseAdminUsersRepository(db)

    old_profile = await user_repo.get_profile(uid)
    old_tier = old_profile.get("tier", "unknown") if old_profile else "unknown"

    subscription_status = "active" if req.tier in ["starter", "pro"] else "inactive"
    await user_repo.update_subscription_tier(uid, req.tier, subscription_status=subscription_status)

    await admin_repo.admin_log_operation(
        admin_id=admin["id"],
        operation_type="tier_change",
        target_user_id=uid,
        details=f"{old_tier} → {req.tier}",
        reason=None,
    )
    return {"status": "ok"}


@router.post("/users/{uid}/tier", deprecated=True)
@limiter.limit("10/minute")
async def update_user_tier(
    request: Request,
    uid: str,
    req: TierUpdateRequest,
    admin: dict = Depends(require_admin),
):
    """
    Update user tier (DEPRECATED - REMOVED in v3.26).

    v3.26 (USER-HIGH-4): This endpoint has been REMOVED due to duplicate code.
    **Please use `PATCH /users/{uid}` instead.**

    Returns:
        410 Gone - This endpoint is no longer available
    """
    raise HTTPException(
        status_code=410,
        detail={
            "error": "Endpoint removed",
            "message": "POST /users/{uid}/tier has been removed in v3.26. Please use PATCH /users/{uid} instead.",
            "replacement_endpoint": f"PATCH /admin/users/{uid}",
            "migration_guide": "Change your request from POST to PATCH and use the same request body."
        }
    )
    return {"status": "ok"}


@router.post("/users/{uid}/discount")
@limiter.limit("10/minute")
async def create_user_discount_api(
    request: Request,
    uid: str,
    req: DiscountRequest,
    admin: dict = Depends(require_admin),
):
    """
    Create a user-specific discount.

    v3.26 (USER-LOW-3): Added admin operation logging
    """
    # v3.25: USER-LOW-2 - Validate uid length
    if len(uid) > 100:
        raise HTTPException(400, "User ID too long (max 100 characters)")

    db = get_database_client()
    user_repo = SupabaseUserRepository(db)
    admin_repo = SupabaseAdminUsersRepository(db)

    discount = await user_repo.create_user_discount(
        uid,
        req.discount_percent,
        req.valid_days,
        req.target_plan,
    )

    # v3.26 (USER-LOW-3): Log admin operation
    await admin_repo.admin_log_operation(
        admin_id=admin["id"],
        operation_type="discount_create",
        target_user_id=uid,
        details=f"{req.discount_percent}% off for {req.valid_days} days" + (f" on {req.target_plan}" if req.target_plan else ""),
        reason=None,
    )

    return discount


@router.get("/users/{uid}/payments")
@limiter.limit("30/minute")
async def get_user_payments(
    request: Request,
    uid: str,
    admin: dict = Depends(require_admin),
):
    """Fetch a user's payment history."""
    # v3.25: USER-LOW-2 - Validate uid length
    if len(uid) > 100:
        raise HTTPException(400, "User ID too long (max 100 characters)")

    db = get_database_client()
    user_repo = SupabaseUserRepository(db)

    profile = await user_repo.get_profile(uid)
    if not profile:
        raise HTTPException(404, "User not found")

    stripe_customer_id = profile.get("stripe_customer_id")
    if not stripe_customer_id:
        return {"payments": [], "message": "No Stripe customer associated"}

    try:
        payments = get_customer_payments(stripe_customer_id)
        return {"payments": payments, "stripe_customer_id": stripe_customer_id}
    except Exception as e:
        # v3.25: USER-LOW-3 - Limited error exposure
        logger.error(f"[Admin] Failed to fetch payments for {uid}: {e}")
        raise HTTPException(500, "Failed to fetch payment history")


@router.get("/users/{uid}/projects")
@limiter.limit("30/minute")
async def get_user_projects(
    request: Request,
    uid: str,
    # v3.25: USER-MEDIUM-2 - Migrated to offset pagination
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return (1-100)"),
    include_deleted: bool = True,
    admin: dict = Depends(require_admin),
):
    """Fetch all projects owned by a specific user."""
    # v3.25: USER-LOW-2 - Validate uid length
    if len(uid) > 100:
        raise HTTPException(400, "User ID too long (max 100 characters)")

    db = get_database_client()
    admin_repo = SupabaseAdminUsersRepository(db)
    return await admin_repo.admin_get_user_projects(uid, offset, limit, include_deleted)


@router.get("/users/{uid}/asset-usage")
@limiter.limit("30/minute")
async def get_user_asset_usage(
    request: Request,
    uid: str,
    top_n: int = 10,
    admin: dict = Depends(require_admin),
):
    """
    Get detailed asset usage for a user.

    v3.26 (USER-CRITICAL-1): Migrated to use SupabaseAssetRepository
    - Fixes: DDD architecture violation (was directly accessing DB)
    - Adds: @retry_on_network_error decorator via Repository
    - Adds: Query limit (1000) to prevent OOM
    - Adds: Configurable top_n parameter
    """
    # v3.25: USER-LOW-2 - Validate uid length
    if len(uid) > 100:
        raise HTTPException(400, "User ID too long (max 100 characters)")

    try:
        # v3.26: Use Repository layer (fixes DDD violation)
        from infrastructure.repositories import SupabaseAssetRepository
        from core.database import get_database_client

        db = get_database_client()
        asset_repo = SupabaseAssetRepository(db)

        # Repository handles query limit, retry logic, and aggregation
        stats = await asset_repo.get_user_asset_usage(uid, limit=1000, top_n=top_n)

        return {
            "user_id": uid,
            **stats
        }
    except Exception as e:
        # v3.25: USER-LOW-3 - Limited error exposure
        logger.error(f"[Admin] Failed to get asset usage for {uid}: {e}")
        raise HTTPException(500, "Failed to retrieve asset usage data")


@router.get("/users/{uid}/env-stats")
@limiter.limit("30/minute")
async def get_user_env_stats(
    request: Request,
    uid: str,
    limit: int = 100,
    admin: dict = Depends(require_admin),
):
    """
    Get detailed user environment statistics.

    v3.26 (USER-CRITICAL-1 + USER-HIGH-1): Migrated to use SupabaseAnalyticsRepository
    - Fixes: DDD architecture violation (was directly accessing DB)
    - Fixes: OOM risk (reduced default limit from 500 to 100)
    - Fixes: Referrer parsing IndexError (safe parsing in Repository)
    - Adds: @retry_on_network_error decorator via Repository
    - Adds: Configurable limit parameter
    """
    # v3.25: USER-LOW-2 - Validate uid length
    if len(uid) > 100:
        raise HTTPException(400, "User ID too long (max 100 characters)")

    try:
        # v3.26: Use Repository layer (fixes DDD violation)
        from infrastructure.repositories import SupabaseAnalyticsRepository
        from core.database import get_database_client

        db = get_database_client()
        analytics_repo = SupabaseAnalyticsRepository(db)

        # Repository handles query limit, retry logic, safe parsing, and aggregation
        stats = await analytics_repo.get_user_env_stats(uid, limit=limit)

        return {
            "user_id": uid,
            "sample_size": stats["total_events"],
            "browsers": stats["browsers"],
            "devices": stats["devices"],
            "os_types": stats["os_stats"],
            "referrers": dict(sorted(stats["referrers"].items(), key=lambda x: x[1], reverse=True)[:10]),
            "screen_sizes": {},  # Not implemented in new version (can add later if needed)
        }
    except Exception as e:
        # v3.25: USER-LOW-3 - Limited error exposure
        logger.error(f"[Admin] Failed to get env stats for {uid}: {e}")
        raise HTTPException(500, "Failed to retrieve environment statistics")


# ==========================================
# Project Management (v3.25: Added rate limiting and validation)
# ==========================================

@router.post("/projects/{project_id}/restore")
@limiter.limit("10/minute")
async def restore_project_api(
    request: Request,
    project_id: str,
    admin: dict = Depends(require_admin),
):
    """Restore a deleted project."""
    # v3.25: USER-LOW-2 - Validate project_id length
    if len(project_id) > 100:
        raise HTTPException(400, "Project ID too long (max 100 characters)")

    db = get_database_client()
    project_repo = SupabaseProjectRepository(db)

    project = await project_repo.restore_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.get("/projects/feed")
@limiter.limit("30/minute")
async def get_projects_feed(
    request: Request,
    # v3.25: USER-MEDIUM-2 - Migrated to offset pagination
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return (1-100)"),
    admin: dict = Depends(require_admin),
):
    """Fetch the site-wide project feed."""
    db = get_database_client()
    project_repo = SupabaseProjectRepository(db)
    items = await project_repo.get_all_projects_feed(offset, limit)
    return {"items": items, "total": len(items), "offset": offset, "limit": limit}
