"""
Database Marketplace - Listing and purchase operations

@module services.db.marketplace
@version 3.24
"""

import logging
from datetime import datetime, timezone

from .core import supabase, retry_on_network_error, listing_is_public_visible

logger = logging.getLogger(__name__)


@retry_on_network_error()
def get_marketplace_listings(resource_type: str = None, sort_by: str = "recent",
                             page: int = 1, limit: int = 20, user_id: str = None):
    """Get marketplace listings with filters."""
    if not supabase:
        return []
    
    offset = (page - 1) * limit
    
    query = supabase.table("marketplace_listings").select("*")\
        .eq("is_public", True).eq("is_deleted", False)\
        .eq("moderation_status", "approved")
    
    if resource_type:
        query = query.eq("resource_type", resource_type)
    
    # Sorting
    if sort_by == "popular":
        query = query.order("sales_count", desc=True)
    elif sort_by == "price_low":
        query = query.order("price")
    elif sort_by == "price_high":
        query = query.order("price", desc=True)
    else:
        query = query.order("created_at", desc=True)
    
    result = query.range(offset, offset + limit - 1).execute()
    return result.data or []


@retry_on_network_error()
def get_marketplace_item(listing_id: str, user_id: str = None):
    """Get single marketplace item."""
    if not supabase:
        return None
    
    result = supabase.table("marketplace_listings").select("*").eq("id", listing_id).execute()
    
    if not result.data:
        return None
    
    listing = result.data[0]
    
    # Check if user has purchased
    if user_id:
        purchase = supabase.table("marketplace_purchases").select("id")\
            .eq("buyer_id", user_id).eq("listing_id", listing_id).execute()
        listing["is_purchased"] = bool(purchase.data)
    
    return listing


@retry_on_network_error()
def get_seller_listings(seller_id: str, page: int = 1, limit: int = 20):
    """Get seller's listings."""
    if not supabase:
        return []
    
    offset = (page - 1) * limit
    result = supabase.table("marketplace_listings").select("*")\
        .eq("user_id", seller_id).eq("is_deleted", False)\
        .order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    
    return result.data or []


@retry_on_network_error()
def create_listing(user_id: str, title: str, description: str, resource_type: str,
                   price: int, resource_id: str = None, preview_images: list = None,
                   resource_data: dict = None, allowed_tiers: list = None):
    """Create new marketplace listing."""
    if not supabase:
        return None
    
    result = supabase.table("marketplace_listings").insert({
        "user_id": user_id,
        "title": title,
        "description": description,
        "resource_type": resource_type,
        "price": price,
        "project_id": resource_id if resource_type == "project" else None,
        "preview_images": preview_images or [],
        "resource_data": resource_data or {},
        "allowed_tiers": allowed_tiers or ["all"],
        "moderation_status": "pending",
        "is_public": False,
    }).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def submit_listing_for_review(listing_id: str, seller_id: str):
    """Submit listing for review."""
    if not supabase:
        return None
    
    result = supabase.table("marketplace_listings").update({
        "moderation_status": "pending",
        "submitted_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", listing_id).eq("user_id", seller_id).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def unpublish_listing(listing_id: str, seller_id: str):
    """Unpublish listing."""
    if not supabase:
        return None
    
    result = supabase.table("marketplace_listings").update({
        "is_public": False
    }).eq("id", listing_id).eq("user_id", seller_id).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def update_listing(listing_id: str, seller_id: str, updates: dict):
    """Update listing."""
    if not supabase:
        return None
    
    result = supabase.table("marketplace_listings").update(updates)\
        .eq("id", listing_id).eq("user_id", seller_id).execute()
    
    return result.data[0] if result.data else None


def check_user_purchase(user_id: str, listing_id: str) -> bool:
    """Check if user has purchased listing."""
    if not supabase:
        return False
    result = supabase.table("marketplace_purchases").select("id")\
        .eq("buyer_id", user_id).eq("listing_id", listing_id).execute()
    return bool(result.data)


@retry_on_network_error()
def execute_purchase(buyer_id: str, listing_id: str, tz: str = "UTC"):
    """Execute marketplace purchase using atomic RPC."""
    if not supabase:
        return {"success": False, "error": "Database not available"}
    
    try:
        result = supabase.rpc("execute_marketplace_purchase", {
            "p_buyer_id": buyer_id,
            "p_listing_id": listing_id,
            "p_timezone": tz
        }).execute()
        
        if result.data:
            return {"success": True, "data": result.data}
        return {"success": False, "error": "RPC returned no data"}
    except Exception as e:
        error_str = str(e)
        if "INSUFFICIENT" in error_str:
            return {"success": False, "error": "INSUFFICIENT_CREDITS"}
        if "ALREADY_PURCHASED" in error_str:
            return {"success": False, "error": "ALREADY_PURCHASED"}
        logger.error(f"execute_purchase failed: {e}")
        return {"success": False, "error": error_str}


@retry_on_network_error()
def get_user_purchases(user_id: str, page: int = 1, limit: int = 50):
    """Get user's purchases."""
    if not supabase:
        return []
    
    offset = (page - 1) * limit
    result = supabase.table("marketplace_purchases").select(
        "*, marketplace_listings(id, title, resource_type, thumbnail_url)"
    ).eq("buyer_id", user_id).order("purchased_at", desc=True)\
    .range(offset, offset + limit - 1).execute()
    
    return result.data or []


@retry_on_network_error()
def get_seller_stats(seller_id: str) -> dict:
    """Get seller statistics."""
    if not supabase:
        return {}
    
    listings = supabase.table("marketplace_listings").select("id, price, sales_count")\
        .eq("user_id", seller_id).eq("is_deleted", False).execute()
    
    data = listings.data or []
    total_sales = sum(l.get("sales_count", 0) for l in data)
    total_revenue = sum(l.get("price", 0) * l.get("sales_count", 0) for l in data)
    
    return {
        "total_listings": len(data),
        "total_sales": total_sales,
        "total_revenue": total_revenue
    }


@retry_on_network_error()
def record_listing_usage(listing_id: str, used_by_user_id: str, project_id: str) -> bool:
    """Record listing usage."""
    if not supabase:
        return False
    
    try:
        supabase.table("listing_usages").insert({
            "listing_id": listing_id,
            "used_by_user_id": used_by_user_id,
            "project_id": project_id,
        }).execute()
        return True
    except:
        return False


@retry_on_network_error()
def get_leaderboard(period: str = "monthly", board_type: str = "all", limit: int = 10):
    """Get marketplace leaderboard."""
    if not supabase:
        return []
    
    # Get top sellers by sales count
    result = supabase.table("marketplace_listings").select(
        "user_id, profiles(username, avatar_url)"
    ).eq("is_deleted", False).order("sales_count", desc=True).limit(limit * 3).execute()
    
    # Aggregate by user
    user_stats = {}
    for item in (result.data or []):
        uid = item.get("user_id")
        if uid not in user_stats:
            user_stats[uid] = {
                "user_id": uid,
                "profile": item.get("profiles"),
                "total_sales": 0
            }
        user_stats[uid]["total_sales"] += 1
    
    # Sort and return top
    sorted_users = sorted(user_stats.values(), key=lambda x: -x["total_sales"])
    return sorted_users[:limit]
