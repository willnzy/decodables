"""
Aggregators Base - Common utilities for aggregation tasks

@module application.services.aggregators.base
@version 3.24
"""

from datetime import datetime, timezone

from core.database import supabase as _supabase_client

# Supabase client singleton
_supabase = None


def get_supabase():
    """Get Supabase client instance."""
    global _supabase
    if _supabase is None:
        _supabase = _supabase_client
    return _supabase


def log(message: str):
    """Log with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def upsert_stats(stat_type: str, data: dict, date: datetime = None):
    """Upsert aggregated statistics."""
    supabase = get_supabase()
    if not supabase:
        return None
    
    if date is None:
        date = datetime.now(timezone.utc)
    
    date_str = date.strftime("%Y-%m-%d")
    
    try:
        result = supabase.table("aggregated_stats").upsert({
            "date": date_str,
            "stat_type": stat_type,
            "data": data,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }, on_conflict="date,stat_type").execute()
        return result.data[0] if result.data else None
    except Exception as e:
        log(f"❌ Error upserting stats {stat_type}: {e}")
        return None


def get_date_range(days: int = 30):
    """Get start and end dates for range queries."""
    now = datetime.now(timezone.utc)
    end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    start = (now - __import__('datetime').timedelta(days=days)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return start, end


def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """Safe division with default value."""
    if b == 0:
        return default
    return a / b
