"""
Admin Repository - Unified admin operations repository.

@module infrastructure.repositories.admin_repository
@version 1.0.0

Consolidates admin user management, stats, and moderation operations.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta

from core.database import DatabaseClient, retry_on_network_error, get_supabase_client

logger = logging.getLogger(__name__)


class SupabaseAdminUsersRepository:

    """Extended repository for admin user management operations."""

    def __init__(self, client):
        self.client = client

    @retry_on_network_error()
    async def get_full_user_audit(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get complete user audit information."""
        profile = self.client.table("profiles").select("*").eq("id", user_id).execute()
        if not profile.data:
            return None
        
        projects = self.client.table("projects").select("id, title, created_at").eq("user_id", user_id).execute()
        transactions = self.client.table("credit_transactions").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(50).execute()
        purchases = self.client.table("marketplace_purchases").select("*").eq("buyer_id", user_id).execute()
        
        return {
            "profile": profile.data[0],
            "projects": projects.data or [],
            "transactions": transactions.data or [],
            "purchases": purchases.data or [],
        }

    @retry_on_network_error()
    async def admin_adjust_credits(self, user_id: str, amount: int, bucket: str, reason: str) -> Optional[Dict[str, Any]]:
        """Admin adjust user credits."""
        profile = self.client.table("profiles").select("credits_monthly, credits_permanent").eq("id", user_id).execute()
        
        if not profile.data:
            return None
        
        current = profile.data[0]
        
        if bucket == "monthly":
            new_value = max(0, current.get("credits_monthly", 0) + amount)
            update = {"credits_monthly": new_value}
        else:
            new_value = max(0, current.get("credits_permanent", 0) + amount)
            update = {"credits_permanent": new_value}
        
        self.client.table("profiles").update(update).eq("id", user_id).execute()
        
        # Log transaction
        self.client.table("credit_transactions").insert({
            "user_id": user_id,
            "amount": abs(amount),
            "bucket": bucket,
            "type": "admin_add" if amount > 0 else "admin_deduct",
            "description": reason,
        }).execute()
        
        return {"success": True, "new_value": new_value}

    @retry_on_network_error()
    async def admin_get_user_projects(self, user_id: str, page: int = 1, limit: int = 20, include_deleted: bool = True) -> List[Dict[str, Any]]:
        """Admin get user's projects."""
        offset = (page - 1) * limit
        query = self.client.table("projects").select("*").eq("user_id", user_id)
        
        if not include_deleted:
            query = query.eq("is_deleted", False)
        
        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return result.data or []

    @retry_on_network_error()
    async def admin_log_operation(self, admin_id: str, operation_type: str, target_user_id: Optional[str] = None,
                            details: Optional[str] = None, reason: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Log admin operation."""
        result = self.client.table("admin_operations").insert({
            "admin_id": admin_id,
            "operation_type": operation_type,
            "target_user_id": target_user_id,
            "details": details,
            "reason": reason,
        }).execute()
        
        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def admin_get_operation_logs(self, page: int = 1, limit: int = 50, operation_type: Optional[str] = None,
                                 admin_id: Optional[str] = None, target_user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get admin operation logs."""
        offset = (page - 1) * limit
        query = self.client.table("admin_operations").select("*", count="exact")
        
        if operation_type:
            query = query.eq("operation_type", operation_type)
        if admin_id:
            query = query.eq("admin_id", admin_id)
        if target_user_id:
            query = query.eq("target_user_id", target_user_id)
        
        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        
        return {"items": result.data or [], "total": result.count or 0}


class SupabaseAdminStatsRepository:

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
    async def log_user_events_batch(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Batch insert user events (optimized for multiple events).

        Args:
            events: List of event dicts with keys: user_id, event_type, properties, session_id, event_id

        Returns:
            List of inserted event records

        Performance:
            - 10 events: 1 DB call instead of 10 (10x improvement)
            - Reference: https://supabase.com/docs/reference/python/insert
        """
        if not events:
            return []

        result = self.client.table("user_events").insert(events).execute()
        return result.data or []

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


class SupabaseAdminModerationRepository:

    """Extended repository for admin content moderation operations."""

    def __init__(self, client):
        self.client = client

    @retry_on_network_error()
    async def admin_get_moderation_list(self, status: str = "pending", page: int = 1, limit: int = 20) -> List[Dict[str, Any]]:
        """Get moderation queue."""
        offset = (page - 1) * limit
        query = self.client.table("marketplace_listings").select(
            "*, profiles(username, email)"
        ).eq("is_deleted", False)
        
        if status:
            query = query.eq("moderation_status", status)
        
        result = query.order("submitted_at", desc=True).range(offset, offset + limit - 1).execute()
        return result.data or []

    @retry_on_network_error()
    async def admin_get_moderation_detail(self, listing_id: str) -> Optional[Dict[str, Any]]:
        """Get listing detail for moderation."""
        result = self.client.table("marketplace_listings").select(
            "*, profiles(username, email, tier)"
        ).eq("id", listing_id).execute()
        
        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def admin_approve_listing(self, listing_id: str, admin_id: str) -> Optional[Dict[str, Any]]:
        """Approve listing."""
        result = self.client.table("marketplace_listings").update({
            "moderation_status": "approved",
            "is_public": True,
            "moderated_at": datetime.now(timezone.utc).isoformat(),
            "moderated_by": admin_id,
        }).eq("id", listing_id).execute()
        
        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def admin_reject_listing(self, listing_id: str, admin_id: str, reason: str) -> Optional[Dict[str, Any]]:
        """Reject listing."""
        result = self.client.table("marketplace_listings").update({
            "moderation_status": "rejected",
            "is_public": False,
            "rejection_reason": reason,
            "moderated_at": datetime.now(timezone.utc).isoformat(),
            "moderated_by": admin_id,
        }).eq("id", listing_id).execute()
        
        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def admin_delete_listing(self, listing_id: str) -> Optional[Dict[str, Any]]:
        """Delete listing."""
        result = self.client.table("marketplace_listings").update({
            "is_deleted": True,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", listing_id).execute()
        
        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def admin_unpublish_listing(self, listing_id: str) -> Optional[Dict[str, Any]]:
        """Unpublish listing."""
        result = self.client.table("marketplace_listings").update({
            "is_public": False,
        }).eq("id", listing_id).execute()
        
        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def admin_get_reports(self, status: Optional[str] = None, page: int = 1, limit: int = 20) -> List[Dict[str, Any]]:
        """Get content reports."""
        offset = (page - 1) * limit
        query = self.client.table("reports").select(
            "*, profiles!reporter_id(username), marketplace_listings(title)"
        )
        
        if status:
            query = query.eq("status", status)
        
        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return result.data or []

    @retry_on_network_error()
    async def admin_get_reports_count(self, status: Optional[str] = None) -> int:
        """Get reports count."""
        query = self.client.table("reports").select("id", count="exact")
        
        if status:
            query = query.eq("status", status)
        
        result = query.execute()
        return result.count or 0

    @retry_on_network_error()
    async def admin_respond_to_report(self, report_id: str, admin_id: str, action: str, response: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Respond to report."""
        result = self.client.table("reports").update({
            "status": action,
            "admin_response": response,
            "responded_by": admin_id,
            "responded_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", report_id).execute()
        
        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def admin_get_report_detail(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get report detail."""
        result = self.client.table("reports").select(
            "*, profiles!reporter_id(username, email), marketplace_listings(*)"
        ).eq("id", report_id).execute()
        
        return result.data[0] if result.data else None


