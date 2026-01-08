"""
Project Statistics Aggregators

@module scheduled_tasks.aggregators.project_stats
@version 3.24
"""

from datetime import datetime, timedelta, timezone
from .base import log, get_supabase, upsert_stats


def aggregate_daily_projects():
    """Aggregate daily project statistics."""
    log("📁 Starting daily projects aggregation...")
    supabase = get_supabase()
    if not supabase:
        return
    
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    for days_ago in range(30):
        date = today - timedelta(days=days_ago)
        next_date = date + timedelta(days=1)
        
        # New projects
        new_projects = supabase.table("projects").select("id", count="exact")\
            .gte("created_at", date.isoformat())\
            .lt("created_at", next_date.isoformat()).execute()
        
        # Active projects (updated)
        active = supabase.table("projects").select("id", count="exact")\
            .gte("updated_at", date.isoformat())\
            .lt("updated_at", next_date.isoformat()).execute()
        
        # Deleted projects
        deleted = supabase.table("projects").select("id", count="exact")\
            .eq("is_deleted", True)\
            .gte("deleted_at", date.isoformat())\
            .lt("deleted_at", next_date.isoformat()).execute()
        
        upsert_stats("daily_projects", {
            "new": new_projects.count or 0,
            "active": active.count or 0,
            "deleted": deleted.count or 0
        }, date)
    
    log("✅ Daily projects complete")


def aggregate_project_details():
    """Aggregate project details statistics."""
    log("📁 Starting project details...")
    supabase = get_supabase()
    if not supabase:
        return
    
    # Total counts
    total = supabase.table("projects").select("id", count="exact")\
        .eq("is_deleted", False).execute()
    
    total_deleted = supabase.table("projects").select("id", count="exact")\
        .eq("is_deleted", True).execute()
    
    # Projects with thumbnails
    with_thumb = supabase.table("projects").select("id", count="exact")\
        .eq("is_deleted", False)\
        .not_.is_("thumbnail_url", "null").execute()
    
    # Get sample for canvas analysis
    sample = supabase.table("projects").select("canvas_data")\
        .eq("is_deleted", False).limit(100).execute()
    
    # Analyze canvas complexity
    simple = medium = complex_proj = 0
    for p in sample.data or []:
        canvas = p.get("canvas_data") or {}
        objects = canvas.get("objects", [])
        count = len(objects) if isinstance(objects, list) else 0
        
        if count < 10:
            simple += 1
        elif count < 50:
            medium += 1
        else:
            complex_proj += 1
    
    upsert_stats("project_details", {
        "total": total.count or 0,
        "deleted": total_deleted.count or 0,
        "with_thumbnail": with_thumb.count or 0,
        "complexity": {
            "simple": simple,
            "medium": medium,
            "complex": complex_proj
        }
    })
    
    log("✅ Project details complete")
