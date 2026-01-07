"""
Admin Stats Repository Extended - Admin statistics operations.

@module infrastructure.repositories.admin_stats_repository_extended
@version 1.0.0
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta

from core.database import retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseAdminStatsRepositoryExtended:
    """Extended repository for admin statistics operations."""

    def __init__(self, client):
        self.client = client

    @staticmethod
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
    async def admin_get_dashboard_stats(self, period: str = "month") -> Dict[str, Any]:
        """Get dashboard statistics."""
        start_date = self._get_period_start(period).isoformat()
        
        total_users = self.client.table("profiles").select("id", count="exact").execute()
        new_users = self.client.table("profiles").select("id", count="exact").gte("created_at", start_date).execute()
        total_projects = self.client.table("projects").select("id", count="exact").eq("is_deleted", False).execute()
        paying = self.client.table("profiles").select("id", count="exact").neq("tier", "free").eq("subscription_status", "active").execute()
        
        return {
            "total_users": total_users.count or 0,
            "new_users": new_users.count or 0,
            "total_projects": total_projects.count or 0,
            "paying_users": paying.count or 0,
        }

    @retry_on_network_error()
    async def admin_get_user_growth_stats(self, start_date: Optional[str] = None, end_date: Optional[str] = None, group_by: str = "day") -> List[Dict[str, Any]]:
        """Get user growth statistics."""
        if not start_date:
            start_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        if not end_date:
            end_date = datetime.now(timezone.utc).isoformat()
        
        result = self.client.table("profiles").select("created_at").gte("created_at", start_date).lte("created_at", end_date).order("created_at").execute()
        
        stats = {}
        for row in (result.data or []):
            date_str = row["created_at"][:10]
            stats[date_str] = stats.get(date_str, 0) + 1
        
        return [{"date": k, "count": v} for k, v in sorted(stats.items())]

    @retry_on_network_error()
    async def admin_get_tier_distribution(self) -> Dict[str, Any]:
        """Get user tier distribution."""
        free = self.client.table("profiles").select("id", count="exact").eq("tier", "free").execute()
        starter = self.client.table("profiles").select("id", count="exact").eq("tier", "starter").execute()
        pro = self.client.table("profiles").select("id", count="exact").eq("tier", "pro").execute()
        
        return {"free": free.count or 0, "starter": starter.count or 0, "pro": pro.count or 0}

    @retry_on_network_error()
    async def admin_get_project_stats(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Get project statistics."""
        if not start_date:
            start_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        if not end_date:
            end_date = datetime.now(timezone.utc).isoformat()
        
        total = self.client.table("projects").select("id", count="exact").eq("is_deleted", False).execute()
        new_in_period = self.client.table("projects").select("id", count="exact").gte("created_at", start_date).lte("created_at", end_date).eq("is_deleted", False).execute()
        
        return {"total": total.count or 0, "new_in_period": new_in_period.count or 0}

    @retry_on_network_error()
    async def admin_get_credit_usage_stats(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Get credit usage statistics."""
        if not start_date:
            start_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        
        result = self.client.table("credit_transactions").select("amount, type").gte("created_at", start_date).execute()
        
        total_used = 0
        by_type = {}
        
        for tx in (result.data or []):
            amount = abs(tx.get("amount", 0))
            tx_type = tx.get("type", "unknown")
            total_used += amount
            by_type[tx_type] = by_type.get(tx_type, 0) + amount
        
        return {"total_used": total_used, "by_type": by_type}

    @retry_on_network_error()
    async def admin_get_conversion_funnel(self, period: str = "month") -> Dict[str, Any]:
        """Get conversion funnel statistics."""
        start_date = self._get_period_start(period).isoformat()
        
        signups = self.client.table("profiles").select("id", count="exact").gte("created_at", start_date).execute()
        created_project = self.client.table("projects").select("user_id").gte("created_at", start_date).execute()
        unique_creators = len(set(p["user_id"] for p in (created_project.data or [])))
        converted = self.client.table("profiles").select("id", count="exact").neq("tier", "free").gte("created_at", start_date).execute()
        
        return {"signups": signups.count or 0, "created_project": unique_creators, "converted": converted.count or 0}

    @retry_on_network_error()
    async def log_user_event(self, user_id: str, event_type: str, properties: Optional[dict] = None,
                       session_id: Optional[str] = None, event_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Log user event."""
        result = self.client.table("user_events").insert({
            "user_id": user_id,
            "event_type": event_type,
            "properties": properties or {},
            "session_id": session_id,
            "event_id": event_id,
        }).execute()
        
        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def admin_get_user_events(self, user_id: Optional[str] = None, event_type: Optional[str] = None,
                              page: int = 1, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user events."""
        offset = (page - 1) * limit
        query = self.client.table("user_events").select("*")
        
        if user_id:
            query = query.eq("user_id", user_id)
        if event_type:
            query = query.eq("event_type", event_type)
        
        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return result.data or []

    @retry_on_network_error()
    async def admin_get_event_stats(self, start_date: Optional[str] = None, end_date: Optional[str] = None, group_by: str = "event_type") -> Dict[str, Any]:
        """Get event statistics."""
        if not start_date:
            start_date = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        
        result = self.client.table("user_events").select("event_type").gte("created_at", start_date).execute()
        
        stats = {}
        for event in (result.data or []):
            et = event.get("event_type", "unknown")
            stats[et] = stats.get(et, 0) + 1
        
        return stats

    @retry_on_network_error()
    async def get_aggregated_stats(self, stat_type: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get aggregated statistics."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        result = self.client.table("aggregated_stats").select("*").eq("stat_type", stat_type).eq("date", today).execute()
        
        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def get_aggregated_stats_range(self, stat_type: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get aggregated stats for date range."""
        start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        result = self.client.table("aggregated_stats").select("*").eq("stat_type", stat_type).gte("date", start).order("date", desc=True).execute()
        
        return result.data or []

    @retry_on_network_error()
    async def upsert_aggregated_stats(self, date_str: str, stat_type: str, data: dict) -> Optional[Dict[str, Any]]:
        """Upsert aggregated statistics."""
        result = self.client.table("aggregated_stats").upsert({
            "date": date_str,
            "stat_type": stat_type,
            "data": data,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="date,stat_type").execute()
        
        return result.data[0] if result.data else None

    # Note: AI functions (admin_get_ai_insights, admin_get_ai_recommendations, admin_get_behavior_analysis)
    # are complex business logic functions that will be kept in services/db/admin_stats.py for now
    # They can be migrated later if needed
