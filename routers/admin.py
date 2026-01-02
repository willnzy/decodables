"""
Admin Router
Handles admin-related API endpoints

@module routers/admin
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from dependencies import require_admin
from db_service import (
    admin_search_users, admin_get_user_audit, admin_adjust_credits,
    admin_update_tier, admin_create_discount, admin_broadcast,
    admin_restore_project, admin_get_projects_feed,
    admin_get_moderation_list, get_marketplace_item,
    admin_approve_listing, admin_reject_listing, 
    admin_delete_listing, admin_unpublish_listing,
    # System Config Functions
    admin_get_system_configs, admin_get_config_groups,
    admin_create_system_config, admin_update_system_config,
    admin_delete_system_config, admin_get_config_audit_logs,
    invalidate_config_cache_api
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# Request Models
class CreditAdjustRequest(BaseModel):
    user_id: str
    amount: int
    bucket: str = "permanent"  # 'monthly' | 'permanent'
    reason: Optional[str] = None


class TierUpdateRequest(BaseModel):
    user_id: str
    tier: str  # 'free' | 'starter' | 'pro'


class DiscountRequest(BaseModel):
    user_id: str
    discount_percent: int
    valid_days: int
    target_plan: Optional[str] = None


class BroadcastRequest(BaseModel):
    title: str
    content: str
    target_group: str = "all"  # 'all' | 'free' | 'starter' | 'pro'


class RejectRequest(BaseModel):
    reason: str


# User Management Routes
@router.get("/users")
def search_users(query: str, admin: dict = Depends(require_admin)):
    """
    Search users by email or username.
    
    Returns:
        Matching users
    """
    return admin_search_users(query)


@router.get("/user/{user_id}")
def get_user_audit(user_id: str, admin: dict = Depends(require_admin)):
    """
    Get full user audit data.
    
    Returns:
        User profile, credits, transactions, projects, etc.
    """
    return admin_get_user_audit(user_id)


@router.post("/credits/adjust")
def adjust_credits(req: CreditAdjustRequest, admin: dict = Depends(require_admin)):
    """
    Adjust user credits.
    
    Args:
        user_id: Target user
        amount: Amount to add (negative to deduct)
        bucket: 'monthly' or 'permanent'
        reason: Reason for adjustment
    
    Returns:
        Updated credit balances
    """
    return admin_adjust_credits(
        req.user_id, 
        req.amount, 
        req.bucket, 
        req.reason,
        admin["id"]
    )


@router.post("/tier/update")
def update_tier(req: TierUpdateRequest, admin: dict = Depends(require_admin)):
    """
    Update user tier.
    
    Returns:
        Updated profile
    """
    return admin_update_tier(req.user_id, req.tier)


@router.post("/discount")
def create_discount(req: DiscountRequest, admin: dict = Depends(require_admin)):
    """
    Create discount for user.
    
    Returns:
        Created discount
    """
    return admin_create_discount(
        req.user_id,
        req.discount_percent,
        req.valid_days,
        req.target_plan
    )


@router.post("/broadcast")
def broadcast(req: BroadcastRequest, admin: dict = Depends(require_admin)):
    """
    Broadcast notification to users.
    
    Returns:
        Created notification
    """
    return admin_broadcast(req.title, req.content, req.target_group)


# Project Management Routes
@router.post("/projects/{project_id}/restore")
def restore_project(project_id: str, admin: dict = Depends(require_admin)):
    """
    Restore a deleted project.
    
    Raises:
        HTTPException: 404 if not found
    
    Returns:
        Restored project
    """
    result = admin_restore_project(project_id)
    if not result:
        raise HTTPException(404, "Project not found")
    return result


@router.get("/projects/feed")
def get_projects_feed(page: int = 1, limit: int = 50, admin: dict = Depends(require_admin)):
    """
    Get all projects feed (time desc).
    
    Returns:
        Projects with user info
    """
    items = admin_get_projects_feed(page, limit)
    return {"items": items, "total": len(items), "page": page}


# Marketplace Moderation Routes
@router.get("/marketplace/moderation/list")
def get_moderation_list(
    status: Optional[str] = None,
    type: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    admin: dict = Depends(require_admin)
):
    """
    Get moderation queue.
    
    Args:
        status: Filter by moderation_status (pending/approved/rejected)
        type: Filter by resource_type (project/asset)
    
    Returns:
        Listings with seller info
    """
    items = admin_get_moderation_list(status, type, page, limit)
    return {"items": items, "total": len(items), "page": page}


@router.get("/marketplace/moderation/{listing_id}")
def get_moderation_detail(listing_id: str, admin: dict = Depends(require_admin)):
    """
    Get listing detail for moderation.
    
    Returns:
        Full listing with seller info
    """
    item = get_marketplace_item(listing_id, admin["id"])
    if not item:
        raise HTTPException(404, "Listing not found")
    return item


@router.post("/marketplace/moderation/{listing_id}/approve")
def approve_listing(listing_id: str, admin: dict = Depends(require_admin)):
    """
    Approve a listing.
    
    Returns:
        Updated listing
    """
    result = admin_approve_listing(listing_id, admin["id"])
    if not result:
        raise HTTPException(404, "Listing not found")
    return {"status": "approved", "listing_id": listing_id}


@router.post("/marketplace/moderation/{listing_id}/reject")
def reject_listing(listing_id: str, req: RejectRequest, admin: dict = Depends(require_admin)):
    """
    Reject a listing with reason.
    
    Returns:
        Updated listing
    """
    result = admin_reject_listing(listing_id, admin["id"], req.reason)
    if not result:
        raise HTTPException(404, "Listing not found")
    return {"status": "rejected", "listing_id": listing_id, "reason": req.reason}


@router.post("/marketplace/moderation/{listing_id}/delete")
def delete_listing(listing_id: str, admin: dict = Depends(require_admin)):
    """
    Soft delete a listing.
    
    Returns:
        Status
    """
    result = admin_delete_listing(listing_id, admin["id"])
    if not result:
        raise HTTPException(404, "Listing not found")
    return {"status": "deleted", "listing_id": listing_id}


@router.post("/marketplace/moderation/{listing_id}/unpublish")
def unpublish_listing(listing_id: str, admin: dict = Depends(require_admin)):
    """
    Force unpublish a listing.
    
    Returns:
        Status
    """
    result = admin_unpublish_listing(listing_id, admin["id"])
    if not result:
        raise HTTPException(404, "Listing not found")
    return {"status": "unpublished", "listing_id": listing_id}


# ==========================================
# System Configuration Routes
# ==========================================

class ConfigCreateRequest(BaseModel):
    key: str
    value: str
    value_type: str = "text"  # 'text', 'boolean', 'json', 'number'
    config_group: str = "general"
    description: Optional[str] = None


class ConfigUpdateRequest(BaseModel):
    value: Optional[str] = None
    value_type: Optional[str] = None
    config_group: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/configs")
def get_configs(
    group: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    admin: dict = Depends(require_admin)
):
    """
    Get all system configs with filtering.
    
    Args:
        group: Filter by config_group
        search: Search in key or description
    
    Returns:
        Paginated configs
    """
    return admin_get_system_configs(group, search, page, limit)


@router.get("/configs/groups")
def get_config_groups(admin: dict = Depends(require_admin)):
    """
    Get all distinct config groups.
    
    Returns:
        List of group names
    """
    groups = admin_get_config_groups()
    return {"groups": groups}


@router.post("/configs")
def create_config(req: ConfigCreateRequest, admin: dict = Depends(require_admin)):
    """
    Create a new system config.
    
    Returns:
        Created config
    """
    try:
        result = admin_create_system_config(
            key=req.key,
            value=req.value,
            value_type=req.value_type,
            config_group=req.config_group,
            description=req.description,
            admin_id=admin["id"]
        )
        if result:
            return {"status": "created", "config": result}
        raise HTTPException(500, "Failed to create config")
    except Exception as e:
        if "duplicate key" in str(e).lower():
            raise HTTPException(409, f"Config key '{req.key}' already exists")
        raise HTTPException(500, str(e))


@router.put("/configs/{key}")
def update_config(key: str, req: ConfigUpdateRequest, admin: dict = Depends(require_admin)):
    """
    Update an existing system config.
    
    Returns:
        Updated config
    """
    try:
        result = admin_update_system_config(
            key=key,
            value=req.value,
            value_type=req.value_type,
            config_group=req.config_group,
            description=req.description,
            is_active=req.is_active,
            admin_id=admin["id"]
        )
        if result:
            return {"status": "updated", "config": result}
        raise HTTPException(404, "Config not found")
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/configs/{key}")
def delete_config(key: str, admin: dict = Depends(require_admin)):
    """
    Delete a system config.
    
    Returns:
        Status
    """
    try:
        result = admin_delete_system_config(key, admin["id"])
        if result:
            return {"status": "deleted", "key": key}
        raise HTTPException(404, "Config not found")
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/configs/audit")
def get_config_audit_logs(
    config_key: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    admin: dict = Depends(require_admin)
):
    """
    Get config change audit logs.
    
    Returns:
        Audit log entries
    """
    logs = admin_get_config_audit_logs(config_key, page, limit)
    return {"items": logs, "page": page}


@router.post("/configs/cache/invalidate")
def invalidate_cache(admin: dict = Depends(require_admin)):
    """
    Manually invalidate all config cache.
    Useful for forcing immediate updates across all instances.
    
    Returns:
        Status
    """
    invalidate_config_cache_api()
    return {"status": "cache_invalidated"}


# ==========================================
# Analytics & Metrics API (v3.12)
# ==========================================
from db_service import supabase
from datetime import date, timedelta


@router.get("/metrics/daily")
def get_daily_metrics(
    days: int = 30,
    admin: dict = Depends(require_admin)
):
    """
    Get daily metrics trend (DAU, new users, AI usage, etc.)
    
    Args:
        days: Number of days to fetch (default 30)
    
    Returns:
        List of daily metrics
    """
    start_date = (date.today() - timedelta(days=days)).isoformat()
    
    result = supabase.table("analytics_daily_metrics").select("*").gte(
        "metric_date", start_date
    ).order("metric_date", desc=True).execute()
    
    return {
        "items": result.data or [],
        "period_days": days
    }


@router.get("/metrics/monthly")
def get_monthly_metrics(
    months: int = 12,
    admin: dict = Depends(require_admin)
):
    """
    Get monthly metrics (MRR, MAU, ARPU, etc.)
    
    Args:
        months: Number of months to fetch (default 12)
    
    Returns:
        List of monthly metrics
    """
    start_date = (date.today() - timedelta(days=months * 30)).replace(day=1).isoformat()
    
    result = supabase.table("analytics_monthly_metrics").select("*").gte(
        "metric_month", start_date
    ).order("metric_month", desc=True).execute()
    
    return {
        "items": result.data or [],
        "period_months": months
    }


@router.get("/metrics/retention")
def get_retention_metrics(admin: dict = Depends(require_admin)):
    """
    Get cohort retention data for retention analysis.
    
    Returns:
        Cohort retention rates
    """
    # Get last 12 weekly cohorts
    result = supabase.table("analytics_cohort_retention").select("*").eq(
        "cohort_type", "week"
    ).order("cohort_date", desc=True).limit(12).execute()
    
    return {
        "cohorts": result.data or [],
        "retention_periods": ["D1", "D7", "D14", "D30", "D60", "D90"]
    }


@router.get("/metrics/funnel")
def get_funnel_metrics(
    days: int = 30,
    admin: dict = Depends(require_admin)
):
    """
    Get conversion funnel metrics.
    
    Returns:
        Funnel stages with conversion rates
    """
    start_date = (date.today() - timedelta(days=days)).isoformat()
    
    result = supabase.table("analytics_funnel_metrics").select("*").eq(
        "funnel_type", "main"
    ).gte("metric_date", start_date).order("metric_date", desc=True).execute()
    
    # Aggregate totals
    totals = {
        "visitors": 0,
        "signups": 0,
        "activated": 0,
        "engaged": 0,
        "converted": 0,
    }
    
    for row in result.data or []:
        totals["visitors"] += row.get("stage_visitors", 0)
        totals["signups"] += row.get("stage_signups", 0)
        totals["activated"] += row.get("stage_activated", 0)
        totals["engaged"] += row.get("stage_engaged", 0)
        totals["converted"] += row.get("stage_converted", 0)
    
    # Calculate overall conversion rates
    rates = {}
    if totals["visitors"] > 0:
        rates["visitor_to_signup"] = round(totals["signups"] / totals["visitors"] * 100, 2)
        rates["visitor_to_converted"] = round(totals["converted"] / totals["visitors"] * 100, 2)
    if totals["signups"] > 0:
        rates["signup_to_activated"] = round(totals["activated"] / totals["signups"] * 100, 2)
        rates["signup_to_converted"] = round(totals["converted"] / totals["signups"] * 100, 2)
    
    return {
        "period_days": days,
        "totals": totals,
        "rates": rates,
        "daily": result.data or []
    }


@router.get("/metrics/errors")
def get_error_metrics(
    days: int = 7,
    admin: dict = Depends(require_admin)
):
    """
    Get error summary for monitoring dashboard.
    
    Returns:
        Top errors with affected users and trend
    """
    start_date = (date.today() - timedelta(days=days)).isoformat()
    
    result = supabase.table("analytics_error_summary").select("*").gte(
        "summary_date", start_date
    ).order("occurrence_count", desc=True).limit(100).execute()
    
    # Group by error code
    error_groups = {}
    for row in result.data or []:
        code = row.get("error_code", "UNKNOWN")
        if code not in error_groups:
            error_groups[code] = {
                "error_code": code,
                "error_type": row.get("error_type"),
                "total_occurrences": 0,
                "total_affected_users": 0,
                "latest_message": row.get("sample_message"),
                "latest_request_id": row.get("sample_request_id"),
                "avg_trend": 0,
                "endpoints": set()
            }
        
        error_groups[code]["total_occurrences"] += row.get("occurrence_count", 0)
        error_groups[code]["total_affected_users"] += row.get("affected_users", 0)
        if row.get("endpoint"):
            error_groups[code]["endpoints"].add(row["endpoint"])
    
    # Convert to list and sort
    top_errors = sorted(
        [
            {**v, "endpoints": list(v["endpoints"])} 
            for v in error_groups.values()
        ],
        key=lambda x: -x["total_occurrences"]
    )[:20]
    
    return {
        "period_days": days,
        "top_errors": top_errors,
        "total_error_types": len(error_groups)
    }


@router.get("/metrics/dau-trend")
def get_dau_trend(admin: dict = Depends(require_admin)):
    """
    Get DAU trend with 7-day moving average (from materialized view).
    
    Returns:
        DAU trend data
    """
    result = supabase.table("mv_dau_trend").select("*").order(
        "metric_date", desc=True
    ).limit(30).execute()
    
    return {
        "trend": result.data or []
    }


@router.post("/metrics/refresh")
def refresh_metrics(admin: dict = Depends(require_admin)):
    """
    Manually trigger metrics ETL.
    
    Returns:
        Status
    """
    try:
        from scheduled_tasks.metrics_etl import run_daily_etl
        run_daily_etl()
        return {"status": "success", "message": "Metrics refresh completed"}
    except Exception as e:
        raise HTTPException(500, f"Metrics refresh failed: {str(e)}")

