"""
Admin Users API - User management endpoints for admins.

@module api.admin.users
@version 2.0.0

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

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from dependencies import require_admin
from core.database import get_supabase_client
from infrastructure.repositories.admin.supabase_admin_users_repository import SupabaseAdminUsersRepositoryExtended
from infrastructure.repositories.admin.supabase_admin_billing_repository import SupabaseAdminBillingRepositoryExtended
from infrastructure.repositories.admin.supabase_admin_logs_repository import SupabaseAdminLogsRepositoryExtended
from infrastructure.repositories.admin.supabase_admin_projects_repository import SupabaseAdminProjectsRepositoryExtended
from domains.billing.payment_service import get_customer_payments

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin-users-v2"])


# ==========================================
# Request Models
# ==========================================

class CreditAdjustRequest(BaseModel):
    """Credit adjustment request."""
    amount: int
    bucket: str = Field("permanent", pattern="^(monthly|permanent)$")
    reason: Optional[str] = None


class TierUpdateRequest(BaseModel):
    """Tier update request."""
    tier: str = Field(..., pattern="^(free|starter|pro)$")


class DiscountRequest(BaseModel):
    """Discount creation request."""
    discount_percent: int = Field(..., ge=1, le=100)
    valid_days: int = Field(7, ge=1, le=365)
    target_plan: Optional[str] = None


# ==========================================
# User Management Endpoints
# ==========================================

@router.get("/users")
async def search_users_api(
    query: str = Query(..., min_length=1),
    admin: dict = Depends(require_admin),
):
    """Search users by query."""
    users_repo = SupabaseAdminUsersRepositoryExtended()
    users = await users_repo.search_users(query)
    return {"users": users}


@router.get("/users/by-tier/{tier}")
async def get_users_by_tier_api(
    tier: str,
    admin: dict = Depends(require_admin),
):
    """Get users by tier (for bulk notifications)."""
    users_repo = SupabaseAdminUsersRepositoryExtended()
    users = await users_repo.get_users_by_tier(tier)
    return {"users": users, "count": len(users), "tier": tier}


@router.get("/users/{uid}")
async def get_user_audit(
    uid: str,
    admin: dict = Depends(require_admin),
):
    """Get full user audit data."""
    users_repo = SupabaseAdminUsersRepositoryExtended()
    return await users_repo.get_full_user_audit(uid)


@router.post("/users/{uid}/credits")
async def adjust_user_credits(
    uid: str,
    req: CreditAdjustRequest,
    admin: dict = Depends(require_admin),
):
    """Manually adjust a user's credits."""
    billing_repo = SupabaseAdminBillingRepositoryExtended()
    logs_repo = SupabaseAdminLogsRepositoryExtended()

    await billing_repo.admin_adjust_credits(uid, req.amount, req.bucket, req.reason)
    await logs_repo.log_activity(admin["id"], "admin_credits_adjust", {
        "target_user": uid,
        "amount": req.amount,
        "bucket": req.bucket,
        "reason": req.reason,
    })
    await logs_repo.admin_log_operation(
        admin_id=admin["id"],
        operation_type="credit_adjust",
        target_user_id=uid,
        details=f"{'+' if req.amount > 0 else ''}{req.amount} {req.bucket} credits",
        reason=req.reason,
    )
    return {"status": "ok"}


@router.patch("/users/{uid}")
async def update_user(
    uid: str,
    req: TierUpdateRequest,
    admin: dict = Depends(require_admin),
):
    """
    Update user properties (tier, etc.).

    **Recommended**: Use PATCH for partial resource updates.
    """
    users_repo = SupabaseAdminUsersRepositoryExtended()
    billing_repo = SupabaseAdminBillingRepositoryExtended()
    logs_repo = SupabaseAdminLogsRepositoryExtended()

    old_profile = await users_repo.get_user_profile(uid)
    old_tier = old_profile.get("tier", "unknown") if old_profile else "unknown"

    subscription_status = "active" if req.tier in ["starter", "pro"] else "inactive"
    await billing_repo.update_subscription_tier(uid, req.tier, subscription_status=subscription_status)

    await logs_repo.log_activity(admin["id"], "admin_tier_update", {
        "target_user": uid,
        "new_tier": req.tier,
        "subscription_status": subscription_status,
    })
    await logs_repo.admin_log_operation(
        admin_id=admin["id"],
        operation_type="tier_change",
        target_user_id=uid,
        details=f"{old_tier} → {req.tier}",
        reason=None,
    )
    return {"status": "ok"}


@router.post("/users/{uid}/tier", deprecated=True)
async def update_user_tier(
    uid: str,
    req: TierUpdateRequest,
    admin: dict = Depends(require_admin),
):
    """
    Update user tier.

    **DEPRECATED**: Use `PATCH /users/{uid}` instead.
    This endpoint will be removed in v3.0.
    """
    users_repo = SupabaseAdminUsersRepositoryExtended()
    billing_repo = SupabaseAdminBillingRepositoryExtended()
    logs_repo = SupabaseAdminLogsRepositoryExtended()

    old_profile = await users_repo.get_user_profile(uid)
    old_tier = old_profile.get("tier", "unknown") if old_profile else "unknown"

    subscription_status = "active" if req.tier in ["starter", "pro"] else "inactive"
    await billing_repo.update_subscription_tier(uid, req.tier, subscription_status=subscription_status)

    await logs_repo.log_activity(admin["id"], "admin_tier_update", {
        "target_user": uid,
        "new_tier": req.tier,
        "subscription_status": subscription_status,
    })
    await logs_repo.admin_log_operation(
        admin_id=admin["id"],
        operation_type="tier_change",
        target_user_id=uid,
        details=f"{old_tier} → {req.tier}",
        reason=None,
    )
    return {"status": "ok"}


@router.post("/users/{uid}/discount")
async def create_user_discount_api(
    uid: str,
    req: DiscountRequest,
    admin: dict = Depends(require_admin),
):
    """Create a user-specific discount."""
    billing_repo = SupabaseAdminBillingRepositoryExtended()
    logs_repo = SupabaseAdminLogsRepositoryExtended()

    discount = await billing_repo.create_user_discount(
        uid,
        req.discount_percent,
        req.valid_days,
        req.target_plan,
    )
    await logs_repo.log_activity(admin["id"], "admin_discount_create", {
        "target_user": uid,
        "discount_percent": req.discount_percent,
    })
    return discount


@router.get("/users/{uid}/payments")
async def get_user_payments(
    uid: str,
    admin: dict = Depends(require_admin),
):
    """Fetch a user's payment history."""
    users_repo = SupabaseAdminUsersRepositoryExtended()

    profile = await users_repo.get_user_profile(uid)
    if not profile:
        raise HTTPException(404, "User not found")

    stripe_customer_id = profile.get("stripe_customer_id")
    if not stripe_customer_id:
        return {"payments": [], "message": "No Stripe customer associated"}

    try:
        payments = get_customer_payments(stripe_customer_id)
        return {"payments": payments, "stripe_customer_id": stripe_customer_id}
    except Exception as e:
        logger.error(f"Failed to fetch payments for {uid}: {e}")
        raise HTTPException(500, f"Failed to fetch payments: {str(e)}")


@router.get("/users/{uid}/projects")
async def get_user_projects(
    uid: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    include_deleted: bool = True,
    admin: dict = Depends(require_admin),
):
    """Fetch all projects owned by a specific user."""
    projects_repo = SupabaseAdminProjectsRepositoryExtended()
    return await projects_repo.admin_get_user_projects(uid, page, limit, include_deleted)


@router.get("/users/{uid}/asset-usage")
async def get_user_asset_usage(
    uid: str,
    admin: dict = Depends(require_admin),
):
    """Get detailed asset usage for a user."""
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
        logger.error(f"Failed to get asset usage for {uid}: {e}")
        raise HTTPException(500, str(e))


@router.get("/users/{uid}/env-stats")
async def get_user_env_stats(
    uid: str,
    admin: dict = Depends(require_admin),
):
    """Get detailed user environment statistics."""
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
        logger.error(f"Failed to get env stats for {uid}: {e}")
        raise HTTPException(500, str(e))


# ==========================================
# Project Management
# ==========================================

@router.post("/projects/{project_id}/restore")
async def restore_project_api(
    project_id: str,
    admin: dict = Depends(require_admin),
):
    """Restore a deleted project."""
    projects_repo = SupabaseAdminProjectsRepositoryExtended()
    logs_repo = SupabaseAdminLogsRepositoryExtended()

    project = await projects_repo.restore_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    await logs_repo.log_activity(admin["id"], "admin_project_restore", {"project_id": project_id})
    return project


@router.get("/projects/feed")
async def get_projects_feed(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    admin: dict = Depends(require_admin),
):
    """Fetch the site-wide project feed."""
    projects_repo = SupabaseAdminProjectsRepositoryExtended()
    items = await projects_repo.get_all_projects_feed(page, limit)
    return {"items": items, "total": len(items), "page": page}
