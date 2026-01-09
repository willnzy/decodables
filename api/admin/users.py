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
    admin: dict = Depends(require_admin),
):
    """Search users by query."""
    db = get_database_client()
    user_repo = SupabaseUserRepository(db)
    users = await user_repo.search_users(query)
    return {"users": users}


@router.get("/users/by-tier/{tier}")
@limiter.limit("30/minute")
async def get_users_by_tier_api(
    request: Request,
    tier: str,
    admin: dict = Depends(require_admin),
):
    """Get users by tier (for bulk notifications)."""
    # v3.25: USER-MEDIUM-3 - Validate tier enum
    tier_lower = tier.lower()
    if tier_lower not in VALID_TIERS:
        raise HTTPException(400, f"Invalid tier. Must be one of: {', '.join(VALID_TIERS)}")

    db = get_database_client()
    user_repo = SupabaseUserRepository(db)
    users = await user_repo.get_users_by_tier(tier_lower)
    return {"users": users, "count": len(users), "tier": tier_lower}


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
    Update user tier.

    **DEPRECATED**: Use `PATCH /users/{uid}` instead.
    This endpoint will be removed in v3.0.
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


@router.post("/users/{uid}/discount")
@limiter.limit("10/minute")
async def create_user_discount_api(
    request: Request,
    uid: str,
    req: DiscountRequest,
    admin: dict = Depends(require_admin),
):
    """Create a user-specific discount."""
    # v3.25: USER-LOW-2 - Validate uid length
    if len(uid) > 100:
        raise HTTPException(400, "User ID too long (max 100 characters)")

    db = get_database_client()
    user_repo = SupabaseUserRepository(db)

    discount = await user_repo.create_user_discount(
        uid,
        req.discount_percent,
        req.valid_days,
        req.target_plan,
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
    admin: dict = Depends(require_admin),
):
    """Get detailed asset usage for a user."""
    # v3.25: USER-LOW-2 - Validate uid length
    if len(uid) > 100:
        raise HTTPException(400, "User ID too long (max 100 characters)")

    supabase = get_supabase_client()

    try:
        assets_result = supabase.table("assets").select("*").eq("user_id", uid).execute()
        assets = assets_result.data if assets_result.data else []

        total_usage = sum(a.get("usage_count", 0) for a in assets)
        by_source = {}
        for a in assets:
            src = a.get("source", "unknown")
            by_source[src] = by_source.get(src, 0) + 1

        return {
            "user_id": uid,
            "total_assets": len(assets),
            "total_usage": total_usage,
            "by_source": by_source,
            "top_used": sorted(assets, key=lambda x: x.get("usage_count", 0), reverse=True)[:10],
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
    admin: dict = Depends(require_admin),
):
    """Get detailed user environment statistics."""
    # v3.25: USER-LOW-2 - Validate uid length
    if len(uid) > 100:
        raise HTTPException(400, "User ID too long (max 100 characters)")

    supabase = get_supabase_client()

    try:
        events = supabase.table("analytics_events").select(
            "properties",
        ).eq("user_id", uid).limit(500).execute()

        events_data = events.data if events.data else []

        browsers = {}
        devices = {}
        screen_sizes = {}
        referrers = {}
        os_types = {}

        for event in events_data:
            props = event.get("properties") or {}

            if browser := props.get("browser"):
                browsers[browser] = browsers.get(browser, 0) + 1
            if device := props.get("device_type"):
                devices[device] = devices.get(device, 0) + 1
            if screen := props.get("screen_size"):
                screen_sizes[screen] = screen_sizes.get(screen, 0) + 1
            if ref := props.get("referrer"):
                domain = ref.split("/")[2] if len(ref.split("/")) > 2 else ref
                referrers[domain] = referrers.get(domain, 0) + 1
            if os_name := props.get("os"):
                os_types[os_name] = os_types.get(os_name, 0) + 1

        return {
            "user_id": uid,
            "sample_size": len(events_data),
            "browsers": browsers,
            "devices": devices,
            "screen_sizes": screen_sizes,
            "referrers": dict(sorted(referrers.items(), key=lambda x: x[1], reverse=True)[:10]),
            "os_types": os_types,
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
