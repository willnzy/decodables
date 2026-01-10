"""
User Statistics Aggregators

@module scheduled_tasks.aggregators.user_stats
@version 3.24
"""

from datetime import datetime, timedelta, timezone
from collections import defaultdict
from .base import log, get_supabase, upsert_stats


def aggregate_daily_user_stats():
    """Aggregate daily user statistics."""
    log("📊 Starting daily user stats aggregation...")
    supabase = get_supabase()
    if not supabase:
        return
    
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    for days_ago in range(30):
        date = today - timedelta(days=days_ago)
        next_date = date + timedelta(days=1)
        
        new_users = supabase.table("profiles").select("id", count="exact")\
            .gte("created_at", date.isoformat())\
            .lt("created_at", next_date.isoformat()).execute()
        
        active_users = supabase.table("activity_logs").select("user_id")\
            .gte("created_at", date.isoformat())\
            .lt("created_at", next_date.isoformat()).execute()
        unique_active = len(set(a.get("user_id") for a in active_users.data or []))
        
        tier_counts = {"t1": 0, "t2": 0, "t3": 0}
        for tier in tier_counts:
            count = supabase.table("profiles").select("id", count="exact")\
                .eq("tier", tier)\
                .gte("created_at", date.isoformat())\
                .lt("created_at", next_date.isoformat()).execute()
            tier_counts[tier] = count.count or 0
        
        upsert_stats("daily_users", {
            "new_users": new_users.count or 0,
            "active_users": unique_active,
            "new_free": tier_counts["t1"],
            "new_starter": tier_counts["t2"],
            "new_pro": tier_counts["t3"]
        }, date)
    
    log("✅ Daily user stats complete")


def aggregate_tier_distribution():
    """Aggregate tier distribution."""
    log("📊 Starting tier distribution...")
    supabase = get_supabase()
    if not supabase:
        return
    
    distribution = {}
    for tier in ["t1", "t2", "t3"]:
        count = supabase.table("profiles").select("id", count="exact").eq("tier", tier).execute()
        distribution[tier] = count.count or 0
    
    distribution["total"] = sum(distribution.values())
    upsert_stats("tier_distribution", distribution)
    log("✅ Tier distribution complete")


def aggregate_retention_stats():
    """Aggregate user retention statistics."""
    log("📊 Starting retention stats...")
    supabase = get_supabase()
    if not supabase:
        return
    
    now = datetime.now(timezone.utc)
    
    # Users who signed up 7, 14, 30 days ago
    retention_data = {}
    for days in [7, 14, 30]:
        signup_start = (now - timedelta(days=days+1)).replace(hour=0, minute=0, second=0)
        signup_end = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0)
        
        cohort = supabase.table("profiles").select("id")\
            .gte("created_at", signup_start.isoformat())\
            .lt("created_at", signup_end.isoformat()).execute()
        
        cohort_ids = [u["id"] for u in (cohort.data or [])]
        if not cohort_ids:
            retention_data[f"day_{days}"] = {"cohort": 0, "retained": 0, "rate": 0}
            continue
        
        recent_active = supabase.table("activity_logs").select("user_id")\
            .in_("user_id", cohort_ids[:100])\
            .gte("created_at", (now - timedelta(days=7)).isoformat()).execute()
        
        retained = len(set(a["user_id"] for a in (recent_active.data or [])))
        rate = round(retained / len(cohort_ids) * 100, 1) if cohort_ids else 0
        
        retention_data[f"day_{days}"] = {
            "cohort": len(cohort_ids),
            "retained": retained,
            "rate": rate
        }
    
    upsert_stats("retention", retention_data)
    log("✅ Retention stats complete")


def aggregate_returning_users():
    """Aggregate returning user statistics."""
    log("📊 Starting returning users...")
    supabase = get_supabase()
    if not supabase:
        return
    
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    for days_ago in range(7):
        date = today - timedelta(days=days_ago)
        next_date = date + timedelta(days=1)
        
        active = supabase.table("activity_logs").select("user_id")\
            .gte("created_at", date.isoformat())\
            .lt("created_at", next_date.isoformat()).execute()
        
        active_ids = list(set(a["user_id"] for a in (active.data or [])))
        if not active_ids:
            upsert_stats("returning_users", {"total": 0, "new": 0, "returning": 0}, date)
            continue
        
        new_users = supabase.table("profiles").select("id")\
            .in_("id", active_ids[:100])\
            .gte("created_at", date.isoformat())\
            .lt("created_at", next_date.isoformat()).execute()
        
        new_count = len(new_users.data or [])
        returning = len(active_ids) - new_count
        
        upsert_stats("returning_users", {
            "total": len(active_ids),
            "new": new_count,
            "returning": max(0, returning)
        }, date)
    
    log("✅ Returning users complete")


def aggregate_tier_trend():
    """Aggregate tier trend over time."""
    log("📊 Starting tier trend...")
    supabase = get_supabase()
    if not supabase:
        return
    
    now = datetime.now(timezone.utc)
    
    for days_ago in range(30):
        date = now - timedelta(days=days_ago)
        date = date.replace(hour=23, minute=59, second=59)
        
        tier_data = {}
        for tier in ["t1", "t2", "t3"]:
            count = supabase.table("profiles").select("id", count="exact")\
                .eq("tier", tier)\
                .lte("created_at", date.isoformat()).execute()
            tier_data[tier] = count.count or 0
        
        upsert_stats("tier_trend", tier_data, date)
    
    log("✅ Tier trend complete")


def aggregate_tier_conversion():
    """Aggregate tier conversion statistics."""
    log("📊 Starting tier conversion...")
    supabase = get_supabase()
    if not supabase:
        return
    
    now = datetime.now(timezone.utc)
    
    # Get credit transactions that indicate tier upgrades
    upgrades = supabase.table("credit_transactions").select("user_id, type")\
        .eq("type", "sub_grant")\
        .gte("created_at", (now - timedelta(days=30)).isoformat()).execute()
    
    upgrade_users = set(u["user_id"] for u in (upgrades.data or []))
    
    # Count conversions by tier
    conversion_data = {"free_to_starter": 0, "free_to_pro": 0, "starter_to_pro": 0}
    
    for uid in list(upgrade_users)[:100]:
        profile = supabase.table("profiles").select("tier").eq("id", uid).execute()
        if profile.data:
            tier = profile.data[0].get("tier")
            if tier == "t2":
                conversion_data["free_to_starter"] += 1
            elif tier == "t3":
                conversion_data["free_to_pro"] += 1
    
    upsert_stats("tier_conversion", conversion_data)
    log("✅ Tier conversion complete")


def aggregate_user_distribution():
    """Aggregate user distribution by region/activity."""
    log("📊 Starting user distribution...")
    supabase = get_supabase()
    if not supabase:
        return
    
    now = datetime.now(timezone.utc)
    
    # By activity level
    activity_dist = {"highly_active": 0, "active": 0, "inactive": 0, "dormant": 0}
    
    all_users = supabase.table("profiles").select("id").execute()
    sample = (all_users.data or [])[:200]
    
    for user in sample:
        activity = supabase.table("activity_logs").select("id", count="exact")\
            .eq("user_id", user["id"])\
            .gte("created_at", (now - timedelta(days=30)).isoformat()).execute()
        
        count = activity.count or 0
        if count > 50:
            activity_dist["highly_active"] += 1
        elif count > 10:
            activity_dist["active"] += 1
        elif count > 0:
            activity_dist["inactive"] += 1
        else:
            activity_dist["dormant"] += 1
    
    upsert_stats("user_distribution", activity_dist)
    log("✅ User distribution complete")
