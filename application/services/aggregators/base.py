"""
Aggregators Base - Common utilities for aggregation tasks

@module application.services.aggregators.base
@version 3.32 (Log Hygiene)

Changes:
- v3.32: Replaced print-based log function with proper logging
- v3.31: 修复 upsert_stats 以匹配数据库约束 UNIQUE(stat_type, stat_key, period_start)
"""

import logging
from datetime import datetime, timezone

from core.database import supabase as _supabase_client

logger = logging.getLogger(__name__)

# Supabase client singleton
_supabase = None


def get_supabase():
    """Get Supabase client instance."""
    global _supabase
    if _supabase is None:
        _supabase = _supabase_client
    return _supabase


def log(message: str):
    """Log using standard logging."""
    logger.info(message)


def upsert_stats(stat_type: str, data: dict, date: datetime = None):
    """
    Upsert aggregated statistics.
    
    v3.31: 修复以匹配数据库约束 UNIQUE(stat_type, stat_key, period_start)
    
    数据库 aggregated_stats 表定义:
    - stat_type: CHECK IN ('daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'custom')
    - stat_key: 指标键 (如 "event_stats", "page_views", "tier_activity")
    - period_start/period_end: 统计周期
    - date: 日期字段 (可选，用于按日期查询)
    - data: JSONB 数据字段
    
    Args:
        stat_type: 原意为统计类型，现映射为 stat_key
        data: 要存储的数据
        date: 统计日期 (默认今天)
    """
    supabase = get_supabase()
    if not supabase:
        return None
    
    if date is None:
        date = datetime.now(timezone.utc)
    
    # 确保 date 是 UTC 时区
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    
    date_str = date.strftime("%Y-%m-%d")
    
    # 计算 period_start 和 period_end (当天 00:00:00 到 23:59:59)
    period_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    period_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    try:
        result = supabase.table("aggregated_stats").upsert({
            "stat_type": "daily",           # 符合 CHECK 约束
            "stat_key": stat_type,          # 使用原 stat_type 作为 key
            "stat_value": 0,                # 数值保持默认
            "data": data,                   # JSONB 数据
            "date": date_str,               # 日期字段
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "metadata": {},
            "updated_at": datetime.now(timezone.utc).isoformat()
        }, on_conflict="stat_type,stat_key,period_start").execute()
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
