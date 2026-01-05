"""
Database Marketplace - Listing and purchase operations

@module services.db.marketplace
@version 3.24
"""

import logging
from datetime import datetime, timezone as timezone_module

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
def create_listing(
    seller_id: str,
    title: str,
    description: str,
    thumbnail_url: str,
    resource_url: str,
    resource_type: str,
    price_credits: int,
    allowed_tiers: list = None,
    submit_for_review: bool = True,
    resource_id: str = None,
    version: str = "1.0",
    changelog: str = "",
    timezone: str = "UTC"
):
    """
    Create or update listing (PRD Chapter 7/8).
    
    If a listing already exists for this resource (by resource_id or resource_url),
    update it with new version; otherwise create a new listing.
    
    Args:
        seller_id: Seller user ID
        title: Listing title
        description: Listing description
        thumbnail_url: Thumbnail image URL
        resource_url: Resource URL (for assets) or ID (for projects)
        resource_type: 'asset' or 'project'
        price_credits: Price in credits
        allowed_tiers: List of tiers that can access
        submit_for_review: Whether to submit for review immediately
        resource_id: The actual resource ID
        version: Version number
        changelog: What's new in this version
        timezone: IANA timezone for transaction snapshot
    
    Returns:
        Created/updated listing
    """
    if not supabase:
        return None
    
    # Check if listing already exists for this resource
    existing_query = supabase.table("marketplace_listings").select("*")\
        .eq("seller_id", seller_id).eq("is_deleted", False)
    
    # Try to find by resource_id first (preferred), then by resource_url
    if resource_id:
        existing_query = existing_query.eq("resource_id", resource_id)
    else:
        existing_query = existing_query.eq("resource_url", resource_url)
    
    existing_res = existing_query.execute()
    existing_listing = existing_res.data[0] if existing_res.data else None
    
    if existing_listing:
        # Update existing listing with new version
        current_history = existing_listing.get("version_history") or []
        
        # Add new version to history
        new_entry = {
            "version": version,
            "changelog": changelog,
            "published_at": datetime.now(timezone_module.utc).isoformat(),
        }
        current_history.append(new_entry)
        
        update_data = {
            "title": title,
            "description": description,
            "thumbnail_url": thumbnail_url,
            "price_credits": price_credits,
            "allowed_tiers": allowed_tiers or ["free"],
            "version": version,
            "changelog": changelog,
            "version_history": current_history,
            "moderation_status": "pending" if submit_for_review else "draft",
            "moderation_note": None,  # Clear previous moderation note
            "is_public": True,
        }
        
        res = supabase.table("marketplace_listings").update(update_data)\
            .eq("id", existing_listing["id"]).execute()
        return res.data[0] if res.data else None
    
    # Create new listing
    version_history = [{
        "version": version,
        "changelog": changelog,
        "published_at": datetime.now(timezone_module.utc).isoformat(),
    }]
    
    data = {
        "seller_id": seller_id,
        "title": title,
        "description": description,
        "thumbnail_url": thumbnail_url,
        "resource_url": resource_url,
        "resource_id": resource_id,
        "resource_type": resource_type,
        "price_credits": price_credits,
        "allowed_tiers": allowed_tiers or ["free"],
        "is_public": True,  # User wants public, but not visible until approved
        "is_deleted": False,
        "sales_count": 0,
        "usage_count": 0,
        "moderation_status": "pending" if submit_for_review else "draft",
        "moderation_note": None,
        "moderated_by": None,
        "moderated_at": None,
        "version": version,
        "changelog": changelog,
        "version_history": version_history,
        "timezone": timezone,
    }
    res = supabase.table("marketplace_listings").insert(data).execute()
    return res.data[0] if res.data else None


@retry_on_network_error()
def submit_listing_for_review(listing_id: str, seller_id: str = None):
    """Submit listing for review."""
    if not supabase:
        return None
    
    query = supabase.table("marketplace_listings").update({
        "moderation_status": "pending",
        "is_public": True,
        "submitted_at": datetime.now(timezone_module.utc).isoformat()
    }).eq("id", listing_id)
    
    if seller_id:
        query = query.eq("seller_id", seller_id)
    
    result = query.execute()
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
