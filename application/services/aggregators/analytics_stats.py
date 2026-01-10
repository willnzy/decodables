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
        .neq("tier", "t1")\
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
    
    for tier in ["t1", "t2", "t3"]:
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
    """
    Aggregate page performance metrics (Core Web Vitals).
    Analyzes Web Vitals and key page timing metrics reported by clients.
    """
    log("⚡ Starting performance metrics aggregation...")
    supabase = get_supabase()
    if not supabase:
        return
    
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=7)).isoformat()
    
    try:
        # Pull performance_metrics events from user_events
        events = supabase.table("user_events").select("properties")\
            .eq("event_type", "performance_metrics")\
            .gte("created_at", start_date).execute()
        
        if not events.data:
            log("  No performance data found")
            return
        
        # Prepare accumulation structures for numeric values and ratings
        metrics_agg = {
            "lcp": {"values": [], "ratings": defaultdict(int)},
            "fid": {"values": [], "ratings": defaultdict(int)},
            "cls": {"values": [], "ratings": defaultdict(int)},
            "fcp": {"values": [], "ratings": defaultdict(int)},
            "ttfb": {"values": [], "ratings": defaultdict(int)},
            "dom_complete": {"values": []},
            "load_complete": {"values": []},
        }
        
        page_metrics = defaultdict(lambda: {"count": 0, "lcp_sum": 0, "fcp_sum": 0})
        
        for event in events.data or []:
            props = event.get("properties", {})
            page_url = props.get("page_url", "/")
            
            # Aggregate each metric value and capture rating buckets
            for metric in ["lcp", "fid", "cls", "fcp", "ttfb", "domComplete", "loadComplete"]:
                key = metric.lower().replace("complete", "_complete")
                value = props.get(metric) or props.get(key)
                if value is not None and isinstance(value, (int, float)):
                    if key in metrics_agg:
                        metrics_agg[key]["values"].append(value)
                    
                    # Track qualitative ratings (good/needs-improvement/poor)
                    rating = props.get(f"{metric}_rating") or props.get(f"{key}_rating")
                    if rating and key in metrics_agg and "ratings" in metrics_agg[key]:
                        metrics_agg[key]["ratings"][rating] += 1
            
            # Build per-page aggregates
            page_metrics[page_url]["count"] += 1
            if lcp := props.get("lcp"):
                page_metrics[page_url]["lcp_sum"] += lcp
            if fcp := props.get("fcp"):
                page_metrics[page_url]["fcp_sum"] += fcp
        
        # Helper function to compute averages and percentiles
        def calc_stats(values):
            if not values:
                return {}
            sorted_v = sorted(values)
            n = len(sorted_v)
            return {
                "count": n,
                "avg": round(sum(sorted_v) / n, 2),
                "p50": sorted_v[n // 2],
                "p90": sorted_v[int(n * 0.9)] if n >= 10 else sorted_v[-1],
                "p95": sorted_v[int(n * 0.95)] if n >= 20 else sorted_v[-1],
            }
        
        # Build final stats dict
        stats = {}
        for metric, data in metrics_agg.items():
            stats[metric] = calc_stats(data["values"])
            if "ratings" in data and data["ratings"]:
                stats[metric]["ratings"] = dict(data["ratings"])
        
        # Add per-page stats (top 10 by page view count)
        top_pages = sorted(page_metrics.items(), key=lambda x: -x[1]["count"])[:10]
        stats["by_page"] = {}
        for page, pdata in top_pages:
            cnt = pdata["count"]
            stats["by_page"][page] = {
                "views": cnt,
                "avg_lcp": round(pdata["lcp_sum"] / cnt, 2) if cnt else 0,
                "avg_fcp": round(pdata["fcp_sum"] / cnt, 2) if cnt else 0,
            }
        
        upsert_stats("performance_metrics", stats)
        log(f"✅ Performance metrics complete: {len(events.data)} events processed")
        
    except Exception as e:
        log(f"⚠️ Performance metrics error: {e}")
