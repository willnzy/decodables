"""
Database Admin Moderation - Content moderation operations

@module services.db.admin_moderation
@version 3.24
"""

import logging
from datetime import datetime, timezone

from core.database import supabase, retry_on_network_error

logger = logging.getLogger(__name__)


@retry_on_network_error()
def admin_get_moderation_list(status: str = "pending", page: int = 1, limit: int = 20):
    """Get moderation queue."""
    if not supabase:
        return []
    
    offset = (page - 1) * limit
    query = supabase.table("marketplace_listings").select(
        "*, profiles(username, email)"
    ).eq("is_deleted", False)
    
    if status:
        query = query.eq("moderation_status", status)
    
    result = query.order("submitted_at", desc=True).range(offset, offset + limit - 1).execute()
    return result.data or []


@retry_on_network_error()
def admin_get_moderation_detail(listing_id: str):
    """Get listing detail for moderation."""
    if not supabase:
        return None
    
    result = supabase.table("marketplace_listings").select(
        "*, profiles(username, email, tier)"
    ).eq("id", listing_id).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def admin_approve_listing(listing_id: str, admin_id: str):
    """Approve listing."""
    if not supabase:
        return None
    
    result = supabase.table("marketplace_listings").update({
        "moderation_status": "approved",
        "is_public": True,
        "moderated_at": datetime.now(timezone.utc).isoformat(),
        "moderated_by": admin_id,
    }).eq("id", listing_id).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def admin_reject_listing(listing_id: str, admin_id: str, reason: str):
    """Reject listing."""
    if not supabase:
        return None
    
    result = supabase.table("marketplace_listings").update({
        "moderation_status": "rejected",
        "is_public": False,
        "rejection_reason": reason,
        "moderated_at": datetime.now(timezone.utc).isoformat(),
        "moderated_by": admin_id,
    }).eq("id", listing_id).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def admin_delete_listing(listing_id: str):
    """Delete listing."""
    if not supabase:
        return None
    
    result = supabase.table("marketplace_listings").update({
        "is_deleted": True,
        "deleted_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", listing_id).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def admin_unpublish_listing(listing_id: str):
    """Unpublish listing."""
    if not supabase:
        return None
    
    result = supabase.table("marketplace_listings").update({
        "is_public": False,
    }).eq("id", listing_id).execute()
    
    return result.data[0] if result.data else None


# ==========================================
# Reports Management
# ==========================================

@retry_on_network_error()
def admin_get_reports(status: str = None, page: int = 1, limit: int = 20):
    """Get content reports."""
    if not supabase:
        return []
    
    offset = (page - 1) * limit
    query = supabase.table("reports").select(
        "*, profiles!reporter_id(username), marketplace_listings(title)"
    )
    
    if status:
        query = query.eq("status", status)
    
    result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return result.data or []


@retry_on_network_error()
def admin_get_reports_count(status: str = None):
    """Get reports count."""
    if not supabase:
        return 0
    
    query = supabase.table("reports").select("id", count="exact")
    
    if status:
        query = query.eq("status", status)
    
    result = query.execute()
    return result.count or 0


@retry_on_network_error()
def admin_respond_to_report(report_id: str, admin_id: str, action: str, response: str = None):
    """Respond to report."""
    if not supabase:
        return None
    
    result = supabase.table("reports").update({
        "status": action,
        "admin_response": response,
        "responded_by": admin_id,
        "responded_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", report_id).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def admin_get_report_detail(report_id: str):
    """Get report detail."""
    if not supabase:
        return None
    
    result = supabase.table("reports").select(
        "*, profiles!reporter_id(username, email), marketplace_listings(*)"
    ).eq("id", report_id).execute()
    
    return result.data[0] if result.data else None
