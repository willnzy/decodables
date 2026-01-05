"""
Database Admin Users - Admin user management operations

@module services.db.admin_users
@version 3.24
"""

import logging
from datetime import datetime, timezone

from .core import supabase, retry_on_network_error
from .users import log_credit_transaction

logger = logging.getLogger(__name__)


@retry_on_network_error()
def get_full_user_audit(user_id: str):
    """Get complete user audit information."""
    if not supabase:
        return None
    
    profile = supabase.table("profiles").select("*").eq("id", user_id).execute()
    if not profile.data:
        return None
    
    projects = supabase.table("projects").select("id, title, created_at")\
        .eq("user_id", user_id).execute()
    
    transactions = supabase.table("credit_transactions").select("*")\
        .eq("user_id", user_id).order("created_at", desc=True).limit(50).execute()
    
    purchases = supabase.table("marketplace_purchases").select("*")\
        .eq("buyer_id", user_id).execute()
    
    return {
        "profile": profile.data[0],
        "projects": projects.data or [],
        "transactions": transactions.data or [],
        "purchases": purchases.data or [],
    }


@retry_on_network_error()
def admin_adjust_credits(user_id: str, amount: int, bucket: str, reason: str):
    """Admin adjust user credits."""
    if not supabase:
        return None
    
    profile = supabase.table("profiles").select("credits_monthly, credits_permanent")\
        .eq("id", user_id).execute()
    
    if not profile.data:
        return None
    
    current = profile.data[0]
    
    if bucket == "monthly":
        new_value = max(0, current.get("credits_monthly", 0) + amount)
        update = {"credits_monthly": new_value}
    else:
        new_value = max(0, current.get("credits_permanent", 0) + amount)
        update = {"credits_permanent": new_value}
    
    supabase.table("profiles").update(update).eq("id", user_id).execute()
    
    log_credit_transaction(
        user_id, abs(amount), bucket,
        "admin_add" if amount > 0 else "admin_deduct",
        reason
    )
    
    return {"success": True, "new_value": new_value}


@retry_on_network_error()
def admin_get_user_projects(user_id: str, page: int = 1, limit: int = 20, include_deleted: bool = True):
    """Admin get user's projects."""
    if not supabase:
        return []
    
    offset = (page - 1) * limit
    query = supabase.table("projects").select("*").eq("user_id", user_id)
    
    if not include_deleted:
        query = query.eq("is_deleted", False)
    
    result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return result.data or []


@retry_on_network_error()
def admin_log_operation(admin_id: str, operation_type: str, target_user_id: str = None,
                        details: str = None, reason: str = None):
    """Log admin operation."""
    if not supabase:
        return None
    
    result = supabase.table("admin_operations").insert({
        "admin_id": admin_id,
        "operation_type": operation_type,
        "target_user_id": target_user_id,
        "details": details,
        "reason": reason,
    }).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def admin_get_operation_logs(page: int = 1, limit: int = 50, operation_type: str = None,
                             admin_id: str = None, target_user_id: str = None):
    """Get admin operation logs."""
    if not supabase:
        return {"items": [], "total": 0}
    
    offset = (page - 1) * limit
    query = supabase.table("admin_operations").select("*", count="exact")
    
    if operation_type:
        query = query.eq("operation_type", operation_type)
    if admin_id:
        query = query.eq("admin_id", admin_id)
    if target_user_id:
        query = query.eq("target_user_id", target_user_id)
    
    result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    
    return {"items": result.data or [], "total": result.count or 0}
