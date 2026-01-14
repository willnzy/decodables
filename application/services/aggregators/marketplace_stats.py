"""
Marketplace Statistics Aggregators

@module scheduled_tasks.aggregators.marketplace_stats
@version 3.24
"""

from datetime import datetime, timedelta, timezone
from .base import log, get_supabase, upsert_stats


def aggregate_marketplace_stats():
    """Aggregate marketplace statistics."""
    log("🛒 Starting marketplace stats...")
    supabase = get_supabase()
    if not supabase:
        return
    
    now = datetime.now(timezone.utc)
    
    # Total listings
    total_listings = supabase.table("marketplace_listings").select("id", count="exact")\
        .eq("is_deleted", False).execute()
    
    # Active listings
    active = supabase.table("marketplace_listings").select("id", count="exact")\
        .eq("is_deleted", False).eq("is_public", True)\
        .eq("moderation_status", "approved").execute()
    
    # Pending moderation
    pending = supabase.table("marketplace_listings").select("id", count="exact")\
        .eq("moderation_status", "pending").execute()
    
    # By type
    types = ["project", "sticker", "background", "character"]
    by_type = {}
    for t in types:
        count = supabase.table("marketplace_listings").select("id", count="exact")\
            .eq("resource_type", t).eq("is_deleted", False).execute()
        by_type[t] = count.count or 0
    
    # Recent sales (7 days)
    recent_sales = supabase.table("marketplace_purchases").select("id", count="exact")\
        .gte("purchased_at", (now - timedelta(days=7)).isoformat()).execute()
    
    # Total revenue (from sales)
    sales = supabase.table("marketplace_purchases").select("price_paid")\
        .gte("purchased_at", (now - timedelta(days=30)).isoformat()).execute()
    
    total_revenue = sum(s.get("price_paid", 0) for s in (sales.data or []))
    
    # Top sellers (Note: marketplace_listings uses seller_id, not user_id)
    listings = supabase.table("marketplace_listings").select("seller_id, sales_count")\
        .eq("is_deleted", False).order("sales_count", desc=True).limit(10).execute()
    
    seller_sales = {}
    for l in listings.data or []:
        uid = l.get("seller_id")
        seller_sales[uid] = seller_sales.get(uid, 0) + l.get("sales_count", 0)
    
    top_sellers = sorted(seller_sales.items(), key=lambda x: -x[1])[:5]
    
    upsert_stats("marketplace", {
        "total_listings": total_listings.count or 0,
        "active_listings": active.count or 0,
        "pending_moderation": pending.count or 0,
        "by_type": by_type,
        "recent_sales_7d": recent_sales.count or 0,
        "revenue_30d": total_revenue,
        "top_sellers": [{"user_id": s[0], "sales": s[1]} for s in top_sellers]
    })
    
    log("✅ Marketplace stats complete")
