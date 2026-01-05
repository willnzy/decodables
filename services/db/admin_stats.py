"""
Database Admin Stats - Admin statistics operations

@module services.db.admin_stats
@version 3.24
"""

import logging
from datetime import datetime, timezone, timedelta

from .core import supabase, retry_on_network_error

logger = logging.getLogger(__name__)


def _get_period_start(period: str) -> datetime:
    """Get start datetime for period."""
    now = datetime.now(timezone.utc)
    if period == "day":
        return now - timedelta(days=1)
    elif period == "week":
        return now - timedelta(weeks=1)
    elif period == "month":
        return now - timedelta(days=30)
    elif period == "year":
        return now - timedelta(days=365)
    return now - timedelta(days=30)


@retry_on_network_error()
def admin_get_dashboard_stats(period: str = "month"):
    """Get dashboard statistics."""
    if not supabase:
        return {}
    
    start_date = _get_period_start(period).isoformat()
    
    # Total users
    total_users = supabase.table("profiles").select("id", count="exact").execute()
    
    # New users in period
    new_users = supabase.table("profiles").select("id", count="exact")\
        .gte("created_at", start_date).execute()
    
    # Total projects
    total_projects = supabase.table("projects").select("id", count="exact")\
        .eq("is_deleted", False).execute()
    
    # Paying users
    paying = supabase.table("profiles").select("id", count="exact")\
        .neq("tier", "free").eq("subscription_status", "active").execute()
    
    return {
        "total_users": total_users.count or 0,
        "new_users": new_users.count or 0,
        "total_projects": total_projects.count or 0,
        "paying_users": paying.count or 0,
    }


@retry_on_network_error()
def admin_get_user_growth_stats(start_date: str = None, end_date: str = None, group_by: str = "day"):
    """Get user growth statistics."""
    if not supabase:
        return []
    
    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    if not end_date:
        end_date = datetime.now(timezone.utc).isoformat()
    
    result = supabase.table("profiles").select("created_at")\
        .gte("created_at", start_date).lte("created_at", end_date)\
        .order("created_at").execute()
    
    # Group by date
    stats = {}
    for row in (result.data or []):
        date_str = row["created_at"][:10]  # YYYY-MM-DD
        stats[date_str] = stats.get(date_str, 0) + 1
    
    return [{"date": k, "count": v} for k, v in sorted(stats.items())]


@retry_on_network_error()
def admin_get_tier_distribution():
    """Get user tier distribution."""
    if not supabase:
        return {}
    
    free = supabase.table("profiles").select("id", count="exact").eq("tier", "free").execute()
    starter = supabase.table("profiles").select("id", count="exact").eq("tier", "starter").execute()
    pro = supabase.table("profiles").select("id", count="exact").eq("tier", "pro").execute()
    
    return {
        "free": free.count or 0,
        "starter": starter.count or 0,
        "pro": pro.count or 0,
    }


@retry_on_network_error()
def admin_get_project_stats(start_date: str = None, end_date: str = None):
    """Get project statistics."""
    if not supabase:
        return {}
    
    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    if not end_date:
        end_date = datetime.now(timezone.utc).isoformat()
    
    total = supabase.table("projects").select("id", count="exact")\
        .eq("is_deleted", False).execute()
    
    new_in_period = supabase.table("projects").select("id", count="exact")\
        .gte("created_at", start_date).lte("created_at", end_date)\
        .eq("is_deleted", False).execute()
    
    return {
        "total": total.count or 0,
        "new_in_period": new_in_period.count or 0,
    }


@retry_on_network_error()
def admin_get_credit_usage_stats(start_date: str = None, end_date: str = None):
    """Get credit usage statistics."""
    if not supabase:
        return {}
    
    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    
    result = supabase.table("credit_transactions").select("amount, type")\
        .gte("created_at", start_date).execute()
    
    total_used = 0
    by_type = {}
    
    for tx in (result.data or []):
        amount = abs(tx.get("amount", 0))
        tx_type = tx.get("type", "unknown")
        total_used += amount
        by_type[tx_type] = by_type.get(tx_type, 0) + amount
    
    return {
        "total_used": total_used,
        "by_type": by_type,
    }


@retry_on_network_error()
def admin_get_conversion_funnel(period: str = "month"):
    """Get conversion funnel statistics."""
    if not supabase:
        return {}
    
    start_date = _get_period_start(period).isoformat()
    
    # Signups
    signups = supabase.table("profiles").select("id", count="exact")\
        .gte("created_at", start_date).execute()
    
    # Created project
    created_project = supabase.table("projects").select("user_id")\
        .gte("created_at", start_date).execute()
    unique_creators = len(set(p["user_id"] for p in (created_project.data or [])))
    
    # Converted to paid
    converted = supabase.table("profiles").select("id", count="exact")\
        .neq("tier", "free").gte("created_at", start_date).execute()
    
    return {
        "signups": signups.count or 0,
        "created_project": unique_creators,
        "converted": converted.count or 0,
    }


# ==========================================
# Events & Aggregated Stats
# ==========================================

@retry_on_network_error()
def log_user_event(user_id: str, event_type: str, properties: dict = None,
                   session_id: str = None, event_id: str = None):
    """Log user event."""
    if not supabase:
        return None
    
    result = supabase.table("user_events").insert({
        "user_id": user_id,
        "event_type": event_type,
        "properties": properties or {},
        "session_id": session_id,
        "event_id": event_id,
    }).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def admin_get_user_events(user_id: str = None, event_type: str = None,
                          page: int = 1, limit: int = 50):
    """Get user events."""
    if not supabase:
        return []
    
    offset = (page - 1) * limit
    query = supabase.table("user_events").select("*")
    
    if user_id:
        query = query.eq("user_id", user_id)
    if event_type:
        query = query.eq("event_type", event_type)
    
    result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return result.data or []


@retry_on_network_error()
def admin_get_event_stats(start_date: str = None, end_date: str = None, group_by: str = "event_type"):
    """Get event statistics."""
    if not supabase:
        return {}
    
    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    
    result = supabase.table("user_events").select("event_type")\
        .gte("created_at", start_date).execute()
    
    stats = {}
    for event in (result.data or []):
        et = event.get("event_type", "unknown")
        stats[et] = stats.get(et, 0) + 1
    
    return stats


@retry_on_network_error()
def get_aggregated_stats(stat_type: str, use_cache: bool = True):
    """Get aggregated statistics."""
    if not supabase:
        return None
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    result = supabase.table("aggregated_stats").select("*")\
        .eq("stat_type", stat_type).eq("date", today).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def get_aggregated_stats_range(stat_type: str, days: int = 30):
    """Get aggregated stats for date range."""
    if not supabase:
        return []
    
    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    result = supabase.table("aggregated_stats").select("*")\
        .eq("stat_type", stat_type).gte("date", start)\
        .order("date", desc=True).execute()
    
    return result.data or []


@retry_on_network_error()
def upsert_aggregated_stats(date_str: str, stat_type: str, data: dict):
    """Upsert aggregated statistics."""
    if not supabase:
        return None
    
    result = supabase.table("aggregated_stats").upsert({
        "date": date_str,
        "stat_type": stat_type,
        "data": data,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="date,stat_type").execute()
    
    return result.data[0] if result.data else None
