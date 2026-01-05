"""
Analytics Statistics Aggregators

@module scheduled_tasks.aggregators.analytics_stats
@version 3.24
"""

from datetime import datetime, timedelta, timezone
from collections import defaultdict
from .base import log, get_supabase, upsert_stats


def aggregate_conversion_funnel():
    """Aggregate conversion funnel statistics."""
    log("📊 Starting conversion funnel...")
    supabase = get_supabase()
    if not supabase:
        return
    
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    
    # Signups
    signups = supabase.table("profiles").select("id", count="exact")\
        .gte("created_at", thirty_days_ago.isoformat()).execute()
    
    # Users who created projects
    project_creators = supabase.table("projects").select("user_id")\
        .gte("created_at", thirty_days_ago.isoformat()).execute()
    unique_creators = len(set(p["user_id"] for p in (project_creators.data or [])))
    
    # Users who used AI
    ai_users = supabase.table("credit_transactions").select("user_id")\
        .ilike("type", "%ai%")\
        .gte("created_at", thirty_days_ago.isoformat()).execute()
    unique_ai = len(set(u["user_id"] for u in (ai_users.data or [])))
    
    # Converted to paid
    paid = supabase.table("profiles").select("id", count="exact")\
        .neq("tier", "free")\
        .gte("created_at", thirty_days_ago.isoformat()).execute()
    
    total_signups = signups.count or 1
    
    upsert_stats("conversion_funnel", {
        "signups": signups.count or 0,
        "created_project": unique_creators,
        "used_ai": unique_ai,
        "converted": paid.count or 0,
        "rates": {
            "signup_to_project": round(unique_creators / total_signups * 100, 1),
            "signup_to_ai": round(unique_ai / total_signups * 100, 1),
            "signup_to_paid": round((paid.count or 0) / total_signups * 100, 1)
        }
    })
    
    log("✅ Conversion funnel complete")


def aggregate_event_stats():
    """Aggregate user event statistics."""
    log("📊 Starting event stats...")
    supabase = get_supabase()
    if not supabase:
        return
    
    now = datetime.now(timezone.utc)
    
    events = supabase.table("user_events").select("event_type")\
        .gte("created_at", (now - timedelta(days=7)).isoformat()).execute()
    
    event_counts = defaultdict(int)
    for e in events.data or []:
        event_counts[e.get("event_type", "unknown")] += 1
    
    sorted_events = sorted(event_counts.items(), key=lambda x: -x[1])
    
    upsert_stats("event_stats", {
        "total": len(events.data or []),
        "by_type": dict(sorted_events[:30])
    })
    
    log("✅ Event stats complete")


def aggregate_page_views():
    """Aggregate page view statistics."""
    log("📊 Starting page views...")
    supabase = get_supabase()
    if not supabase:
        return
    
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    for days_ago in range(7):
        date = today - timedelta(days=days_ago)
        next_date = date + timedelta(days=1)
        
        # Count page_view events
        views = supabase.table("user_events").select("properties")\
            .eq("event_type", "page_view")\
            .gte("created_at", date.isoformat())\
            .lt("created_at", next_date.isoformat()).execute()
        
        page_counts = defaultdict(int)
        for v in views.data or []:
            props = v.get("properties") or {}
            page = props.get("page", "unknown")
            page_counts[page] += 1
        
        upsert_stats("page_views", {
            "total": len(views.data or []),
            "by_page": dict(sorted(page_counts.items(), key=lambda x: -x[1])[:20])
        }, date)
    
    log("✅ Page views complete")


def aggregate_tier_activity():
    """Aggregate activity by tier."""
    log("📊 Starting tier activity...")
    supabase = get_supabase()
    if not supabase:
        return
    
    now = datetime.now(timezone.utc)
    
    tier_activity = {}
    
    for tier in ["free", "starter", "pro"]:
        # Get users of this tier
        users = supabase.table("profiles").select("id").eq("tier", tier).limit(100).execute()
        user_ids = [u["id"] for u in (users.data or [])]
        
        if not user_ids:
            tier_activity[tier] = {"users": 0, "avg_activity": 0}
            continue
        
        # Count their activity
        total_activity = 0
        for uid in user_ids[:50]:
            activity = supabase.table("activity_logs").select("id", count="exact")\
                .eq("user_id", uid)\
                .gte("created_at", (now - timedelta(days=7)).isoformat()).execute()
            total_activity += activity.count or 0
        
        avg = total_activity / len(user_ids[:50]) if user_ids else 0
        
        tier_activity[tier] = {
            "users": len(users.data or []),
            "avg_activity": round(avg, 1)
        }
    
    upsert_stats("tier_activity", tier_activity)
    log("✅ Tier activity complete")


def aggregate_performance_metrics():
    """Aggregate performance metrics."""
    log("📊 Starting performance metrics...")
    supabase = get_supabase()
    if not supabase:
        return
    
    now = datetime.now(timezone.utc)
    
    # API response times (from logs if available)
    # This is a placeholder - real implementation would parse logs
    
    # Database query counts
    query_stats = {
        "profiles": 0,
        "projects": 0,
        "assets": 0,
        "marketplace": 0
    }
    
    # Count recent queries per table (approximation via activity)
    for table in query_stats:
        count = supabase.table("activity_logs").select("id", count="exact")\
            .ilike("action", f"%{table}%")\
            .gte("created_at", (now - timedelta(hours=1)).isoformat()).execute()
        query_stats[table] = count.count or 0
    
    # Error rate (from error logs if available)
    errors = supabase.table("error_logs").select("id", count="exact")\
        .gte("created_at", (now - timedelta(hours=1)).isoformat()).execute() if supabase else None
    
    upsert_stats("performance", {
        "table_activity": query_stats,
        "errors_1h": errors.count if errors else 0,
        "timestamp": now.isoformat()
    })
    
    log("✅ Performance metrics complete")
