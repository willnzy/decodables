"""
Database Assets - Asset CRUD operations

@module services.db.assets
@version 3.24
"""

import logging
from datetime import datetime, timezone

from core.database import supabase, retry_on_network_error

logger = logging.getLogger(__name__)


@retry_on_network_error()
def save_asset(user_id: str, url: str, asset_type: str, project_id: str = None, 
               prompt: str = None, tz: str = "UTC"):
    """Save new asset."""
    if not supabase:
        return None
    
    result = supabase.table("assets").insert({
        "user_id": user_id,
        "url": url,
        "source": asset_type,
        "project_id": project_id,
        "prompt": prompt,
        "timezone": tz,
    }).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def get_assets(user_id: str, project_id: str = None):
    """Get user assets."""
    if not supabase:
        return []
    
    query = supabase.table("assets").select("*").eq("user_id", user_id).eq("is_deleted", False)
    
    if project_id:
        query = query.eq("project_id", project_id)
    
    result = query.order("created_at", desc=True).execute()
    return result.data or []


@retry_on_network_error()
def soft_delete_asset(asset_id: str, user_id: str):
    """Soft delete asset."""
    if not supabase:
        return None
    
    result = supabase.table("assets").update({
        "is_deleted": True,
        "deleted_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", asset_id).eq("user_id", user_id).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def permanently_hide_asset(asset_id: str, user_id: str):
    """Permanently hide asset."""
    if not supabase:
        return None
    
    result = supabase.table("assets").update({
        "is_permanently_deleted": True
    }).eq("id", asset_id).eq("user_id", user_id).eq("is_deleted", True).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def restore_asset(asset_id: str, user_id: str):
    """Restore soft-deleted asset."""
    if not supabase:
        return None
    
    result = supabase.table("assets").update({
        "is_deleted": False,
        "deleted_at": None
    }).eq("id", asset_id).eq("user_id", user_id).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def get_deleted_assets(user_id: str, page: int = 1, limit: int = 20):
    """Get user's deleted assets."""
    if not supabase:
        return []
    
    offset = (page - 1) * limit
    result = supabase.table("assets").select("id, url, source, deleted_at")\
        .eq("user_id", user_id).eq("is_deleted", True)\
        .eq("is_permanently_deleted", False)\
        .order("deleted_at", desc=True).range(offset, offset + limit - 1).execute()
    
    return result.data or []


@retry_on_network_error()
def increment_asset_usage(asset_id: str, user_id: str):
    """Increment asset usage count."""
    if not supabase:
        return None
    
    # Get current count
    asset = supabase.table("assets").select("usage_count").eq("id", asset_id).execute()
    if not asset.data:
        return None
    
    current = asset.data[0].get("usage_count", 0)
    
    result = supabase.table("assets").update({
        "usage_count": current + 1
    }).eq("id", asset_id).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def get_dashboard_assets(user_id: str, view: str = "all", page: int = 1, limit: int = 20):
    """Get assets for dashboard."""
    if not supabase:
        return {"items": [], "total": 0}
    
    offset = (page - 1) * limit
    
    query = supabase.table("assets").select("*", count="exact")\
        .eq("user_id", user_id).eq("is_deleted", False)
    
    result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    
    return {"items": result.data or [], "total": result.count or 0}


@retry_on_network_error()
def get_seller_asset_stats(user_id: str):
    """Get seller statistics for assets."""
    if not supabase:
        return {}
    
    listings = supabase.table("marketplace_listings").select("id, price, sales_count")\
        .eq("user_id", user_id).neq("resource_type", "project").execute()
    
    data = listings.data or []
    total_sales = sum(l.get("sales_count", 0) for l in data)
    total_revenue = sum(l.get("price", 0) * l.get("sales_count", 0) for l in data)
    
    return {
        "total_listings": len(data),
        "total_sales": total_sales,
        "total_revenue": total_revenue
    }


def get_system_resources(resource_type: str = "sticker", user_tier: str = "free"):
    """Get system resources by type."""
    if not supabase:
        return []
    
    result = supabase.table("system_resources").select("*")\
        .eq("resource_type", resource_type).eq("is_active", True)\
        .order("sort_order").execute()
    
    return result.data or []
