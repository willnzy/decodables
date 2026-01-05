"""
AI Reports Collectors - Data collection functions

@module services.ai_reports.collectors
@version 3.24
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple
from collections import defaultdict

from ..db import supabase
from .models import MetricData, UserBehaviorTrend

logger = logging.getLogger(__name__)


def get_date_ranges() -> Dict[str, Tuple[datetime, datetime]]:
    """Get standard date ranges for metrics."""
    now = datetime.now(timezone.utc)
    
    return {
        "current": (now - timedelta(days=30), now),
        "previous": (now - timedelta(days=60), now - timedelta(days=30)),
        "year_ago": (now - timedelta(days=395), now - timedelta(days=365)),
    }


def collect_growth_metrics() -> List[MetricData]:
    """Collect user growth metrics."""
    if not supabase:
        return []
    
    metrics = []
    ranges = get_date_ranges()
    
    try:
        # Total users
        current_users = supabase.table("profiles").select("id", count="exact")\
            .lte("created_at", ranges["current"][1].isoformat()).execute()
        
        previous_users = supabase.table("profiles").select("id", count="exact")\
            .lte("created_at", ranges["previous"][1].isoformat()).execute()
        
        year_ago_users = supabase.table("profiles").select("id", count="exact")\
            .lte("created_at", ranges["year_ago"][1].isoformat()).execute()
        
        metrics.append(MetricData(
            name="Total Users",
            current_value=current_users.count or 0,
            previous_value=previous_users.count or 0,
            year_ago_value=year_ago_users.count,
        ))
        
        # New users this period
        new_current = supabase.table("profiles").select("id", count="exact")\
            .gte("created_at", ranges["current"][0].isoformat())\
            .lte("created_at", ranges["current"][1].isoformat()).execute()
        
        new_previous = supabase.table("profiles").select("id", count="exact")\
            .gte("created_at", ranges["previous"][0].isoformat())\
            .lte("created_at", ranges["previous"][1].isoformat()).execute()
        
        metrics.append(MetricData(
            name="New Signups (30d)",
            current_value=new_current.count or 0,
            previous_value=new_previous.count or 0,
        ))
        
    except Exception as e:
        logger.error(f"Failed to collect growth metrics: {e}")
    
    return metrics


def collect_conversion_metrics() -> List[MetricData]:
    """Collect conversion funnel metrics."""
    if not supabase:
        return []
    
    metrics = []
    ranges = get_date_ranges()
    
    try:
        # Signups to paid conversion
        total = supabase.table("profiles").select("id", count="exact")\
            .gte("created_at", ranges["current"][0].isoformat()).execute()
        
        paid = supabase.table("profiles").select("id", count="exact")\
            .neq("tier", "free")\
            .gte("created_at", ranges["current"][0].isoformat()).execute()
        
        current_rate = (paid.count / total.count * 100) if total.count else 0
        
        # Previous period
        total_prev = supabase.table("profiles").select("id", count="exact")\
            .gte("created_at", ranges["previous"][0].isoformat())\
            .lte("created_at", ranges["previous"][1].isoformat()).execute()
        
        paid_prev = supabase.table("profiles").select("id", count="exact")\
            .neq("tier", "free")\
            .gte("created_at", ranges["previous"][0].isoformat())\
            .lte("created_at", ranges["previous"][1].isoformat()).execute()
        
        prev_rate = (paid_prev.count / total_prev.count * 100) if total_prev.count else 0
        
        metrics.append(MetricData(
            name="Signup-to-Paid Conversion",
            current_value=current_rate,
            previous_value=prev_rate,
            is_percentage=True,
        ))
        
    except Exception as e:
        logger.error(f"Failed to collect conversion metrics: {e}")
    
    return metrics


def collect_retention_metrics() -> List[MetricData]:
    """Collect retention metrics."""
    if not supabase:
        return []
    
    metrics = []
    
    try:
        # Get aggregated retention stats
        stats = supabase.table("aggregated_stats").select("data")\
            .eq("stat_type", "retention").order("date", desc=True).limit(1).execute()
        
        if stats.data:
            data = stats.data[0].get("data", {})
            for period, info in data.items():
                if isinstance(info, dict) and "rate" in info:
                    metrics.append(MetricData(
                        name=f"Retention {period}",
                        current_value=info["rate"],
                        previous_value=info["rate"] * 0.95,  # Approximate
                        is_percentage=True,
                    ))
        
    except Exception as e:
        logger.error(f"Failed to collect retention metrics: {e}")
    
    return metrics


def collect_product_metrics() -> List[MetricData]:
    """Collect product usage metrics."""
    if not supabase:
        return []
    
    metrics = []
    ranges = get_date_ranges()
    
    try:
        # Total projects
        projects = supabase.table("projects").select("id", count="exact")\
            .eq("is_deleted", False).execute()
        
        prev_projects = supabase.table("projects").select("id", count="exact")\
            .eq("is_deleted", False)\
            .lte("created_at", ranges["previous"][1].isoformat()).execute()
        
        metrics.append(MetricData(
            name="Total Projects",
            current_value=projects.count or 0,
            previous_value=prev_projects.count or 0,
        ))
        
        # AI generations
        gen_current = supabase.table("credit_transactions").select("id", count="exact")\
            .ilike("type", "%ai%")\
            .gte("created_at", ranges["current"][0].isoformat()).execute()
        
        gen_previous = supabase.table("credit_transactions").select("id", count="exact")\
            .ilike("type", "%ai%")\
            .gte("created_at", ranges["previous"][0].isoformat())\
            .lte("created_at", ranges["previous"][1].isoformat()).execute()
        
        metrics.append(MetricData(
            name="AI Generations (30d)",
            current_value=gen_current.count or 0,
            previous_value=gen_previous.count or 0,
        ))
        
    except Exception as e:
        logger.error(f"Failed to collect product metrics: {e}")
    
    return metrics


def collect_user_behavior_trends() -> List[UserBehaviorTrend]:
    """Collect user behavior trend data."""
    if not supabase:
        return []
    
    trends = []
    
    try:
        # Get daily stats
        stats = supabase.table("aggregated_stats").select("date, data")\
            .eq("stat_type", "daily_users")\
            .order("date", desc=True).limit(30).execute()
        
        if stats.data:
            daily_active = []
            for row in reversed(stats.data):
                date_str = row.get("date", "")[:10]
                data = row.get("data", {})
                daily_active.append((date_str, data.get("active_users", 0)))
            
            trends.append(UserBehaviorTrend(
                metric_name="Daily Active Users",
                daily_values=daily_active,
            ))
        
    except Exception as e:
        logger.error(f"Failed to collect behavior trends: {e}")
    
    return trends
