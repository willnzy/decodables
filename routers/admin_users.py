"""
Admin Users Router - User management endpoints for admins

@module routers.admin_users
@version 3.24

Endpoints:
- GET /api/admin/users - Search users
- GET /api/admin/user/{uid} - Get user audit
- POST /api/admin/credits/adjust - Adjust credits
- POST /api/admin/tier/update - Update tier
- POST /api/admin/discount - Create discount
- GET /api/admin/user/{uid}/payments - Get payment history
- GET /api/admin/users/by-tier/{tier} - Get users by tier
- GET /api/admin/user/{uid}/projects - Get user projects
- GET /api/admin/user/{uid}/asset-usage - Get asset usage
- GET /api/admin/user/{uid}/env-stats - Get env stats
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

from services.db_service import (
    supabase,
    search_users,
    get_full_user_audit,
    admin_adjust_credits,
    get_user_profile,
    update_subscription_tier,
    create_user_discount,
    admin_log_operation,
    admin_get_user_projects,
    get_users_by_tier,
    log_activity,
)
from services.payment_service import get_customer_payments
from services.rate_limiter import limiter
from dependencies import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin-users"])


# ==========================================
# Request Models
# ==========================================

class AdminAdjustRequest(BaseModel):
    user_id: str
    amount: int
    bucket: str = "permanent"  # "monthly" or "permanent"
    reason: Optional[str] = None


class AdminTierRequest(BaseModel):
    user_id: str
    tier: str  # "free", "starter", "pro"


class AdminDiscountRequest(BaseModel):
    user_id: str
    discount_percent: int
    valid_days: int = 7
    target_plan: Optional[str] = None


# ==========================================
# User Management Endpoints
# ==========================================

@router.get("/users")
@limiter.limit("60/minute")
def adm_users(request: Request, query: str, admin: dict = Depends(require_admin)):
    """Search users by query."""
    users = search_users(query)
    return {"users": users}


@router.get("/user/{uid}")
def adm_audit(uid: str, admin: dict = Depends(require_admin)):
    """Get full user audit data."""
    return get_full_user_audit(uid)


@router.post("/credits/adjust")
@limiter.limit("30/minute")
def adm_adj(request: Request, req: AdminAdjustRequest, admin: dict = Depends(require_admin)):
    """Manually adjust a user's credits (supports bucket selection)."""
    admin_adjust_credits(req.user_id, req.amount, req.bucket, req.reason)
    log_activity(admin["id"], "admin_credits_adjust", {
        "target_user": req.user_id,
        "amount": req.amount,
        "bucket": req.bucket,
        "reason": req.reason
    })
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="credit_adjust",
        target_user_id=req.user_id,
        details=f"{'+' if req.amount > 0 else ''}{req.amount} {req.bucket} credits",
        reason=req.reason
    )
    return {"status": "ok"}


@router.post("/tier/update")
@limiter.limit("30/minute")
def adm_tier(request: Request, req: AdminTierRequest, admin: dict = Depends(require_admin)):
    """Update user tier."""
    old_profile = get_user_profile(req.user_id)
    old_tier = old_profile.get("tier", "unknown") if old_profile else "unknown"
    
    subscription_status = "active" if req.tier in ["starter", "pro"] else "inactive"
    update_subscription_tier(req.user_id, req.tier, subscription_status=subscription_status)
    
    log_activity(admin["id"], "admin_tier_update", {
        "target_user": req.user_id,
        "new_tier": req.tier,
        "subscription_status": subscription_status
    })
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="tier_change",
        target_user_id=req.user_id,
        details=f"{old_tier} → {req.tier}",
        reason=None
    )
    return {"status": "ok"}


@router.post("/discount")
def adm_discount(req: AdminDiscountRequest, admin: dict = Depends(require_admin)):
    """Create a user-specific discount."""
    discount = create_user_discount(
        req.user_id, 
        req.discount_percent, 
        req.valid_days, 
        req.target_plan
    )
    log_activity(admin["id"], "admin_discount_create", {
        "target_user": req.user_id,
        "discount_percent": req.discount_percent
    })
    return discount


@router.get("/user/{uid}/payments")
def adm_user_payments(uid: str, admin: dict = Depends(require_admin)):
    """Fetch a user's payment history (for refund workflows)."""
    profile = get_user_profile(uid)
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


@router.get("/users/by-tier/{tier}")
def adm_users_by_tier(tier: str, admin: dict = Depends(require_admin)):
    """Get users by tier (for bulk notifications)."""
    users = get_users_by_tier(tier)
    return {"users": users, "count": len(users), "tier": tier}


@router.get("/user/{uid}/projects")
def adm_user_projects(uid: str, admin: dict = Depends(require_admin)):
    """Get all projects for a user (admin view)."""
    return admin_get_user_projects(uid)


@router.get("/user/{uid}/asset-usage")
def adm_user_asset_usage(uid: str, admin: dict = Depends(require_admin)):
    """Get detailed asset usage for a user."""
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
            "top_used": sorted(assets, key=lambda x: x.get("usage_count", 0), reverse=True)[:10]
        }
    except Exception as e:
        logger.error(f"Failed to get asset usage for {uid}: {e}")
        raise HTTPException(500, str(e))


@router.get("/user/{uid}/env-stats")
def adm_user_env_stats(uid: str, admin: dict = Depends(require_admin)):
    """Get detailed user environment statistics (browser, device, etc.)."""
    try:
        events = supabase.table("analytics_events").select(
            "properties"
        ).eq("user_id", uid).limit(500).execute()
        
        events_data = events.data if events.data else []
        
        browsers = {}
        devices = {}
        screen_sizes = {}
        referrers = {}
        os_types = {}
        
        for event in events_data:
            props = event.get("properties") or {}
            
            browser = props.get("browser")
            if browser:
                browsers[browser] = browsers.get(browser, 0) + 1
            
            device = props.get("device_type")
            if device:
                devices[device] = devices.get(device, 0) + 1
            
            screen = props.get("screen_size")
            if screen:
                screen_sizes[screen] = screen_sizes.get(screen, 0) + 1
            
            ref = props.get("referrer")
            if ref:
                domain = ref.split("/")[2] if len(ref.split("/")) > 2 else ref
                referrers[domain] = referrers.get(domain, 0) + 1
            
            os_name = props.get("os")
            if os_name:
                os_types[os_name] = os_types.get(os_name, 0) + 1
        
        return {
            "user_id": uid,
            "sample_size": len(events_data),
            "browsers": browsers,
            "devices": devices,
            "screen_sizes": screen_sizes,
            "referrers": dict(sorted(referrers.items(), key=lambda x: x[1], reverse=True)[:10]),
            "os_types": os_types
        }
    except Exception as e:
        logger.error(f"Failed to get env stats for {uid}: {e}")
        raise HTTPException(500, str(e))
