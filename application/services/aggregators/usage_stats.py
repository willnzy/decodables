"""
Usage Statistics Aggregators

@module scheduled_tasks.aggregators.usage_stats
@version 3.24
"""

from datetime import datetime, timedelta, timezone
from collections import defaultdict
from .base import log, get_supabase, upsert_stats


def aggregate_credit_usage():
    """Aggregate credit usage statistics."""
    log("💳 Starting credit usage aggregation...")
    supabase = get_supabase()
    if not supabase:
        return
    
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    for days_ago in range(30):
        date = today - timedelta(days=days_ago)
        next_date = date + timedelta(days=1)
        
        txs = supabase.table("credit_transactions").select("amount, type")\
            .gte("created_at", date.isoformat())\
            .lt("created_at", next_date.isoformat()).execute()
        
        by_type = defaultdict(int)
        total_used = 0
        
        for tx in txs.data or []:
            amount = abs(tx.get("amount", 0))
            tx_type = tx.get("type", "other")
            by_type[tx_type] += amount
            if tx.get("amount", 0) < 0:
                total_used += amount
        
        upsert_stats("credit_usage", {
            "total_used": total_used,
            "by_type": dict(by_type)
        }, date)
    
    log("✅ Credit usage complete")


def aggregate_generation_stats():
    """Aggregate AI generation statistics."""
    log("🤖 Starting generation stats...")
    supabase = get_supabase()
    if not supabase:
        return
    
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    for days_ago in range(7):
        date = today - timedelta(days=days_ago)
        next_date = date + timedelta(days=1)
        
        # Count from credit transactions with generation-related types
        gen_types = ["ai_story", "ai_images", "ai_chat", "ai_inspiration"]
        generation_data = {}
        
        for gen_type in gen_types:
            count = supabase.table("credit_transactions").select("id", count="exact")\
                .eq("type", gen_type)\
                .gte("created_at", date.isoformat())\
                .lt("created_at", next_date.isoformat()).execute()
            generation_data[gen_type] = count.count or 0
        
        generation_data["total"] = sum(generation_data.values())
        
        upsert_stats("generation_stats", generation_data, date)
    
    log("✅ Generation stats complete")


def aggregate_feature_usage():
    """Aggregate feature usage statistics."""
    log("🔧 Starting feature usage...")
    supabase = get_supabase()
    if not supabase:
        return
    
    now = datetime.now(timezone.utc)
    
    # Get activity logs from last 7 days
    activities = supabase.table("activity_logs").select("action")\
        .gte("created_at", (now - timedelta(days=7)).isoformat()).execute()
    
    feature_counts = defaultdict(int)
    for act in activities.data or []:
        action = act.get("action", "unknown")
        feature_counts[action] += 1
    
    # Top features
    sorted_features = sorted(feature_counts.items(), key=lambda x: -x[1])[:20]
    
    upsert_stats("feature_usage", {
        "features": dict(sorted_features),
        "total_actions": sum(feature_counts.values())
    })
    
    log("✅ Feature usage complete")


def aggregate_export_stats():
    """Aggregate export statistics."""
    log("📤 Starting export stats...")
    supabase = get_supabase()
    if not supabase:
        return
    
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    for days_ago in range(30):
        date = today - timedelta(days=days_ago)
        next_date = date + timedelta(days=1)
        
        # Count export-related activities
        exports = supabase.table("activity_logs").select("action")\
            .ilike("action", "%export%")\
            .gte("created_at", date.isoformat())\
            .lt("created_at", next_date.isoformat()).execute()
        
        export_types = defaultdict(int)
        for exp in exports.data or []:
            export_types[exp.get("action", "export")] += 1
        
        upsert_stats("export_stats", {
            "total": len(exports.data or []),
            "by_type": dict(export_types)
        }, date)
    
    log("✅ Export stats complete")


def aggregate_asset_usage():
    """Aggregate asset usage statistics."""
    log("🎨 Starting asset usage...")
    supabase = get_supabase()
    if not supabase:
        return
    
    # Total assets
    total = supabase.table("assets").select("id", count="exact")\
        .eq("is_deleted", False).execute()
    
    # By source type
    sources = ["ai_generated", "uploaded", "system"]
    by_source = {}
    
    for source in sources:
        count = supabase.table("assets").select("id", count="exact")\
            .eq("source", source).eq("is_deleted", False).execute()
        by_source[source] = count.count or 0
    
    # Recent uploads (7 days)
    now = datetime.now(timezone.utc)
    recent = supabase.table("assets").select("id", count="exact")\
        .eq("is_deleted", False)\
        .gte("created_at", (now - timedelta(days=7)).isoformat()).execute()
    
    upsert_stats("asset_usage", {
        "total": total.count or 0,
        "by_source": by_source,
        "recent_7d": recent.count or 0
    })
    
    log("✅ Asset usage complete")
