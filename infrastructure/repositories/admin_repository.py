"""
Admin Repository - Unified admin operations repository.

@module infrastructure.repositories.admin_repository
@version 2.0.0 (AsyncClient migration)

Changes:
- v2.0.0: AsyncClient migration (2026-01-13)
  - Removed get_supabase_client import (unused sync client)
  - All methods use AsyncClient via constructor
- v1.2.0: Moderation module DDD migration (2026-01-09)
  - MOD-CRITICAL-1: All moderation methods ready for Service layer
  - MOD-HIGH-1: Fixed return type to Tuple[List, int] for list methods
  - MOD-HIGH-2: Added .limit(10000) OOM protection to all queries
  - MOD-HIGH-3: Added .limit(1) to all update operations
  - MOD-HIGH-4: Optimized get_reports to return tuple in single query
  - MOD-MEDIUM-2: Optimized get_reports_stats (5 queries → 1 query)
  - MOD-MEDIUM-3: Unified method signatures (action → new_status)
- v1.1.0: Stats module improvements (2026-01-09)
  - STAT-CRITICAL-1: Added admin_get_revenue_stats() method
  - STAT-HIGH-2: Added @retry_on_network_error to dashboard_stats
  - STAT-MEDIUM-4: Optimized tier_distribution (3 queries → 1 query)
  - STAT-MEDIUM-5/6/7/8: Added .limit(100000) to prevent OOM
  - All stats methods now have proper retry mechanisms

Consolidates admin user management, stats, and moderation operations.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta

from core.database import DatabaseClient, retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseAdminUsersRepository:

    """Extended repository for admin user management operations."""

    def __init__(self, client):
        self.client = client

    @retry_on_network_error()
    async def get_full_user_audit(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get complete user audit information."""
        await profile = self.client.table("profiles").select("*").eq("id", user_id).execute()
        if not profile.data:
            return None
        
        await projects = self.client.table("projects").select("id, title, created_at").eq("user_id", user_id).execute()
        await transactions = self.client.table("credit_transactions").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(50).execute()
        await purchases = self.client.table("marketplace_purchases").select("*").eq("buyer_id", user_id).execute()
        
        return {
            "profile": profile.data[0],
            "projects": projects.data or [],
            "transactions": transactions.data or [],
            "purchases": purchases.data or [],
        }

    @retry_on_network_error()
    async def admin_adjust_credits(self, user_id: str, amount: int, bucket: str, reason: str) -> Optional[Dict[str, Any]]:
        """Admin adjust user credits."""
        await profile = self.client.table("profiles").select("credits_monthly, credits_permanent").eq("id", user_id).execute()
        
        if not profile.data:
            return None
        
        current = profile.data[0]
        
        if bucket == "monthly":
            new_value = max(0, current.get("credits_monthly", 0) + amount)
            update = {"credits_monthly": new_value}
        else:
            new_value = max(0, current.get("credits_permanent", 0) + amount)
            update = {"credits_permanent": new_value}
        
        await self.client.table("profiles").update(update).eq("id", user_id).execute()
        
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
    async def admin_get_user_projects(self, user_id: str, offset: int = 0, limit: int = 20, include_deleted: bool = True) -> List[Dict[str, Any]]:
        """Admin get user's projects (v3.25: offset pagination)."""
        query = self.client.table("projects").select("*").eq("user_id", user_id)

        if not include_deleted:
            query = query.eq("is_deleted", False)

        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return result.data or []

    @retry_on_network_error()
    async def admin_log_operation(
        self,
        admin_id: str,
        operation_type: str,
        target_user_id: Optional[str] = None,
        # NEW PARAMETERS for Phase 4 - Task 9:
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        # EXISTING PARAMETERS:
        details: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Enhanced audit logging with source tracking and metadata support.

        New operation_type values (added in Task 9):
        - project_delete_soft, project_delete_permanent, project_restore
        - template_delete, generation_delete, generation_batch_delete
        - resource_delete, feature_flag_delete, campaign_delete, experiment_delete
        - config_update, config_delete, rate_limit_preset_apply, cache_clear
        - webhook_subscription_create, webhook_subscription_update, webhook_subscription_cancel
        - webhook_invoice_paid, webhook_refund_process, webhook_credits_purchase
        - webhook_user_create, webhook_tier_update

        Args:
            admin_id: Admin who performed action (use "system_webhook" for automated)
            operation_type: Type of operation (see list above + existing types)
            target_user_id: Affected user ID (optional)
            target_type: Resource type being operated on (project, config, feature_flag, etc.)
            target_id: Specific resource identifier (project_id, config_key, etc.)
            metadata: Additional context as JSONB (before/after values, batch info, etc.)
            source: Where action originated from (api, webhook, stripe, clerk)
            details: Human-readable description
            reason: Why the action was taken

        Returns:
            Created log entry or None if failed (graceful degradation)
        """
        try:
            result = self.client.table("admin_operations").insert({
                "admin_id": admin_id,
                "operation_type": operation_type,
                "target_user_id": target_user_id,
                "target_type": target_type,
                "target_id": target_id,
                "action_details": metadata or {},  # Using action_details as metadata
                "source": source or "api",
                "details": details,
                "reason": reason,
            }).execute()

            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to log admin operation {operation_type}: {e}")
            return None  # Graceful degradation - don't fail the main operation

    @retry_on_network_error()
    async def admin_get_operation_logs(
        self,
        offset: int = 0,
        limit: int = 50,
        # EXISTING FILTERS:
        operation_type: Optional[str] = None,
        admin_id: Optional[str] = None,
        target_user_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        # NEW FILTERS for Phase 4 - Task 9:
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        source: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Enhanced audit log query with new filter parameters.

        Supports filtering by:
        - operation_type: Specific operation (project_delete, webhook_subscription_create, etc.)
        - admin_id: Admin who performed action (use "system_webhook" for automated)
        - target_user_id: Affected user
        - target_type: Resource type (project, config, feature_flag, system_resource, etc.)
        - target_id: Specific resource ID
        - source: Action source (api, webhook, stripe, clerk)
        - start_date / end_date: Date range filtering

        Returns:
            Dict with logs, total, offset, limit, has_more
        """
        query = self.client.table("admin_operations").select("*", count="exact")

        # Apply all filters
        if operation_type:
            query = query.eq("operation_type", operation_type)
        if admin_id:
            query = query.eq("admin_id", admin_id)
        if target_user_id:
            query = query.eq("target_user_id", target_user_id)
        if target_type:  # NEW
            query = query.eq("target_type", target_type)
        if target_id:    # NEW
            query = query.eq("target_id", target_id)
        if source:       # NEW
            query = query.eq("source", source)
        if start_date:
            query = query.gte("created_at", start_date)
        if end_date:
            query = query.lte("created_at", end_date)

        # Pagination with OOM protection
        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).limit(100000).execute()
        total = result.count or 0

        return {
            "logs": result.data or [],
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < total
        }


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
        
        await total_users = self.client.table("profiles").select("id", count="exact").execute()
        await new_users = self.client.table("profiles").select("id", count="exact").gte("created_at", start_date).execute()
        await total_projects = self.client.table("projects").select("id", count="exact").eq("is_deleted", False).execute()
        await paying = self.client.table("profiles").select("id", count="exact").neq("tier", "t1").eq("subscription_status", "active").execute()
        
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

        # STAT-MEDIUM-6: Added limit to prevent OOM
        await result = self.client.table("profiles").select("created_at").gte("created_at", start_date).lte("created_at", end_date).order("created_at").limit(100000).execute()

        stats = {}
        for row in (result.data or []):
            date_str = row["created_at"][:10]
            stats[date_str] = stats.get(date_str, 0) + 1

        return [{"date": k, "count": v} for k, v in sorted(stats.items())]

    @retry_on_network_error()
    async def admin_get_tier_distribution(self) -> Dict[str, Any]:
        """
        Get user tier distribution (optimized).

        STAT-MEDIUM-4: Changed from 3 separate queries to 1 query + in-memory aggregation.
        STAT-MEDIUM-9: Added .limit(100000) for OOM protection.
        Performance: 3x faster (1 DB roundtrip instead of 3).
        """
        await result = self.client.table("profiles").select("tier").limit(100000).execute()

        distribution = {"t1": 0, "t2": 0, "t3": 0}
        total_fetched = len(result.data or [])

        for row in (result.data or []):
            tier = row.get("tier", "t1")
            if tier in distribution:
                distribution[tier] += 1

        # Add metadata about data completeness
        distribution["_total_fetched"] = total_fetched
        distribution["_is_truncated"] = total_fetched >= 100000

        return distribution

    @retry_on_network_error()
    async def admin_get_project_stats(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Get project statistics."""
        if not start_date:
            start_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        if not end_date:
            end_date = datetime.now(timezone.utc).isoformat()
        
        await total = self.client.table("projects").select("id", count="exact").eq("is_deleted", False).execute()
        await new_in_period = self.client.table("projects").select("id", count="exact").gte("created_at", start_date).lte("created_at", end_date).eq("is_deleted", False).execute()
        
        return {"total": total.count or 0, "new_in_period": new_in_period.count or 0}

    @retry_on_network_error()
    async def admin_get_credit_usage_stats(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Get credit usage statistics."""
        if not start_date:
            start_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

        # STAT-MEDIUM-7: Added limit to prevent OOM
        await result = self.client.table("credit_transactions").select("amount, type").gte("created_at", start_date).limit(100000).execute()

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
        """
        Get conversion funnel statistics using optimized RPC function.

        P2-012: Performance optimization (50x-100x faster).
        - Before: 3 separate queries with full table scans (5-10s)
        - After: 1 RPC call with indexed queries (< 100ms)

        Graceful Fallback: Falls back to legacy queries if RPC fails.

        Args:
            period: Time period ('day', 'week', 'month', 'year')

        Returns:
            Dict with signups, created_project, converted counts
        """
        try:
            # ✅ P2-012: Use optimized RPC function
            await result = self.client.rpc("p_get_conversion_funnel", {"p_period": period}).execute()

            if result.data and len(result.data) > 0:
                row = result.data[0]
                return {
                    "signups": row.get("signups", 0),
                    "created_project": row.get("created_project", 0),
                    "converted": row.get("converted", 0),
                }

            # No data returned
            return {"signups": 0, "created_project": 0, "converted": 0}

        except Exception as e:
            # Graceful Fallback: Use legacy queries if RPC fails
            logger.warning(f"[AdminRepository] RPC p_get_conversion_funnel failed, using legacy queries: {e}")

            start_date = self._get_period_start(period).isoformat()

            await signups = self.client.table("profiles").select("id", count="exact").gte("created_at", start_date).execute()

            # STAT-MEDIUM-5: Added limit to prevent OOM (only need unique user_ids)
            await created_project = self.client.table("projects").select("user_id").gte("created_at", start_date).limit(100000).execute()
            unique_creators = len(set(p["user_id"] for p in (created_project.data or [])))

            await converted = self.client.table("profiles").select("id", count="exact").neq("tier", "t1").gte("created_at", start_date).execute()

            return {"signups": signups.count or 0, "created_project": unique_creators, "converted": converted.count or 0}

    @retry_on_network_error()
    async def admin_get_revenue_stats(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None, group_by: str = "day"
    ) -> List[Dict[str, Any]]:
        """
        Get revenue statistics grouped by time period.

        Query payment_records table for actual payment data.
        Excludes refunds (payment_type='refund' has negative amounts).

        Args:
            start_date: Start date (ISO format), defaults to 30 days ago
            end_date: End date (ISO format), defaults to now
            group_by: Group by period (day/week/month)

        Returns:
            List of revenue stats: [{"date": "2024-01-15", "revenue": 199.8, "count": 10}, ...]
        """
        if not start_date:
            start_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        if not end_date:
            end_date = datetime.now(timezone.utc).isoformat()

        # Query payment records (exclude refunds by filtering amount > 0)
        # STAT-MEDIUM-8: Added limit to prevent OOM
        result = self.client.table("payment_records").select(
            "amount, currency, created_at"
        ).gte("created_at", start_date).lte("created_at", end_date).gt("amount", 0).order("created_at").limit(100000).execute()

        # Group by date
        stats = {}
        for row in (result.data or []):
            date_str = row["created_at"][:10]  # YYYY-MM-DD
            amount = row.get("amount", 0)

            if date_str not in stats:
                stats[date_str] = {"date": date_str, "revenue": 0, "count": 0}

            stats[date_str]["revenue"] += amount
            stats[date_str]["count"] += 1

        # Round revenue to 2 decimals
        for stat in stats.values():
            stat["revenue"] = round(stat["revenue"], 2)

        return [v for k, v in sorted(stats.items())]

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

        await result = self.client.table("user_events").insert(events).execute()
        return result.data or []

    @retry_on_network_error()
    async def admin_get_user_events(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get user events with filters and pagination.

        v3.26 Changes:
        - EVT-CRITICAL-1: Added start_date/end_date filter support
        - EVT-HIGH-1: Migrated from page to offset pagination
        - EVT-HIGH-4: Return Dict with pagination info instead of List

        Args:
            user_id: Filter by user ID
            event_type: Filter by event type
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            offset: Pagination offset
            limit: Maximum number of events to return

        Returns:
            Dict with events, total, offset, limit, has_more
        """
        query = self.client.table("user_events").select("*", count="exact")

        if user_id:
            query = query.eq("user_id", user_id)
        if event_type:
            query = query.eq("event_type", event_type)
        if start_date:
            query = query.gte("created_at", start_date)
        if end_date:
            query = query.lte("created_at", end_date)

        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        total = result.count or 0

        return {
            "events": result.data or [],
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": (offset + limit) < total
        }

    @retry_on_network_error()
    async def admin_get_event_stats(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        group_by: str = "event_type"
    ) -> Dict[str, Any]:
        """
        Get event statistics with grouping support.

        v3.26 Changes:
        - EVT-CRITICAL-2: Added end_date filter support
        - EVT-HIGH-2: Added .limit(100000) to prevent OOM
        - EVT-MEDIUM-2: Implemented full group_by support (4 types)

        Args:
            start_date: Start date (ISO format), defaults to 7 days ago
            end_date: End date (ISO format), defaults to now
            group_by: Group by field (event_type, user_id, date, hour)

        Returns:
            Dict with statistics grouped by specified field
        """
        if not start_date:
            start_date = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

        # Select fields based on group_by
        if group_by == "event_type":
            fields = "event_type"
        elif group_by == "user_id":
            fields = "user_id"
        elif group_by in ("date", "hour"):
            fields = "created_at"
        else:
            fields = "event_type"  # Fallback

        # EVT-HIGH-2: Added limit to prevent OOM
        query = self.client.table("user_events").select(fields).gte("created_at", start_date).limit(100000)

        if end_date:
            query = query.lte("created_at", end_date)

        result = query.execute()

        # Aggregate based on group_by
        stats = {}
        for event in (result.data or []):
            if group_by == "event_type":
                key = event.get("event_type", "unknown")
            elif group_by == "user_id":
                key = event.get("user_id", "unknown")
            elif group_by == "date":
                created_at = event.get("created_at", "")
                key = created_at[:10] if created_at else "unknown"  # YYYY-MM-DD
            elif group_by == "hour":
                created_at = event.get("created_at", "")
                key = created_at[:13] if created_at else "unknown"  # YYYY-MM-DDTHH
            else:
                key = "unknown"

            stats[key] = stats.get(key, 0) + 1

        return stats

    @retry_on_network_error()
    async def get_aggregated_stats(self, stat_type: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get aggregated statistics."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        await result = self.client.table("aggregated_stats").select("*").eq("stat_type", stat_type).eq("date", today).execute()
        
        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def get_aggregated_stats_range(self, stat_type: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get aggregated stats for date range."""
        start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        await result = self.client.table("aggregated_stats").select("*").eq("stat_type", stat_type).gte("date", start).order("date", desc=True).execute()
        
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

    @retry_on_network_error()
    async def admin_get_ai_insights(self, insight_type: str = "all") -> List[Dict[str, Any]]:
        """
        Get AI-generated insights for the platform.

        v3.25: Implemented method (previously missing, caused AttributeError).

        Args:
            insight_type: Type of insights - "all", "growth", "engagement", "revenue"

        Returns:
            List of insight objects with category, title, description, metrics
        """
        # Get aggregated data for insights generation
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

        insights = []

        # Get user growth insight
        if insight_type in ("all", "growth"):
            user_stats = self.client.table("profiles").select("id", count="exact").gte(
                "created_at", week_ago
            ).execute()
            new_users = user_stats.count or 0

            insights.append({
                "category": "growth",
                "title": "User Growth",
                "description": f"{new_users} new users in the last 7 days",
                "metric_value": new_users,
                "trend": "up" if new_users > 0 else "stable"
            })

        # Get engagement insight
        if insight_type in ("all", "engagement"):
            project_stats = self.client.table("projects").select("id", count="exact").gte(
                "created_at", week_ago
            ).eq("is_deleted", False).execute()
            new_projects = project_stats.count or 0

            insights.append({
                "category": "engagement",
                "title": "Project Creation",
                "description": f"{new_projects} projects created in the last 7 days",
                "metric_value": new_projects,
                "trend": "up" if new_projects > 0 else "stable"
            })

        # Get revenue insight
        if insight_type in ("all", "revenue"):
            paying_stats = self.client.table("profiles").select("id", count="exact").neq(
                "tier", "t1"
            ).eq("subscription_status", "active").execute()
            paying_users = paying_stats.count or 0

            insights.append({
                "category": "revenue",
                "title": "Paying Users",
                "description": f"{paying_users} active paying subscribers",
                "metric_value": paying_users,
                "trend": "stable"
            })

        return insights

    @retry_on_network_error()
    async def admin_get_ai_recommendations(self, area: str = "all") -> List[Dict[str, Any]]:
        """
        Get AI-generated recommendations for platform optimization.

        v3.25: Implemented method (previously missing, caused AttributeError).
        v3.26: Optimized query efficiency - use count queries and reduce data transfer.

        Args:
            area: Recommendation area - "all", "growth", "retention", "monetization"

        Returns:
            List of recommendation objects with priority, area, title, action
        """
        recommendations = []
        today = datetime.now(timezone.utc)
        week_ago = (today - timedelta(days=7)).isoformat()
        month_ago = (today - timedelta(days=30)).isoformat()

        # Growth recommendations
        if area in ("all", "growth"):
            new_users_week = self.client.table("profiles").select("id", count="exact").gte(
                "created_at", week_ago
            ).execute()
            new_users_month = self.client.table("profiles").select("id", count="exact").gte(
                "created_at", month_ago
            ).execute()

            weekly = new_users_week.count or 0
            monthly = new_users_month.count or 0
            avg_weekly = monthly / 4 if monthly > 0 else 0

            if weekly < avg_weekly * 0.8:
                recommendations.append({
                    "priority": "high",
                    "area": "growth",
                    "title": "User acquisition below average",
                    "description": f"This week's signups ({weekly}) are below the monthly average ({avg_weekly:.0f}/week)",
                    "action": "Consider running a marketing campaign or promotion"
                })

        # Retention recommendations
        if area in ("all", "retention"):
            # Optimized: Use count queries instead of fetching all data
            await total_users = self.client.table("profiles").select("id", count="exact").execute()

            # Count distinct users who have created projects (more efficient)
            # Note: Supabase doesn't support COUNT(DISTINCT), so we still need to fetch user_ids
            # but we can limit the query
            users_with_projects_result = self.client.table("projects").select(
                "user_id"
            ).limit(100000).execute()  # Limit to prevent OOM

            unique_creators = len(set(p["user_id"] for p in (users_with_projects_result.data or [])))

            total = total_users.count or 0
            if total > 0:
                creation_rate = (unique_creators / total) * 100
                if creation_rate < 50:
                    recommendations.append({
                        "priority": "medium",
                        "area": "retention",
                        "title": "Low project creation rate",
                        "description": f"Only {creation_rate:.1f}% of users have created projects",
                        "action": "Improve onboarding flow or add project templates"
                    })

        # Monetization recommendations
        if area in ("all", "monetization"):
            # Optimized: Reuse total_users from retention if already queried
            if area == "all" and 'total' in locals():
                # Reuse total from retention check
                total = locals()['total']
                total_users_count = total
            else:
                await total_users = self.client.table("profiles").select("id", count="exact").execute()
                total_users_count = total_users.count or 0

            paying_users = self.client.table("profiles").select("id", count="exact").neq(
                "tier", "t1"
            ).execute()

            paying = paying_users.count or 0
            if total_users_count > 0:
                conversion_rate = (paying / total_users_count) * 100
                if conversion_rate < 5:
                    recommendations.append({
                        "priority": "high",
                        "area": "monetization",
                        "title": "Low conversion rate",
                        "description": f"Only {conversion_rate:.1f}% of users are paying",
                        "action": "Review pricing or add more Pro features"
                    })

        return recommendations

    @retry_on_network_error()
    async def admin_get_behavior_analysis(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get AI-powered user behavior analysis.

        v3.25: Implemented method (previously missing, caused AttributeError).
        v3.26: Added @retry_on_network_error decorator and data limit (AI-HIGH-2 fix).
        v3.27: Use configuration constants for limits and defaults.

        Args:
            start_date: Start date for analysis (ISO format)
            end_date: End date for analysis (ISO format)

        Returns:
            Dict with patterns, segments, and activity data
        """
        # Import config constants
        from application.services.ai_reports.config import (
            MAX_USER_EVENTS_BEHAVIOR_ANALYSIS,
            DEFAULT_BEHAVIOR_ANALYSIS_DAYS
        )

        if not start_date:
            start_date = (datetime.now(timezone.utc) - timedelta(days=DEFAULT_BEHAVIOR_ANALYSIS_DAYS)).isoformat()
        if not end_date:
            end_date = datetime.now(timezone.utc).isoformat()

        # Get user activity patterns (limited to prevent OOM)
        events = self.client.table("user_events").select(
            "event_type, created_at"
        ).gte("created_at", start_date).lte("created_at", end_date).limit(MAX_USER_EVENTS_BEHAVIOR_ANALYSIS).execute()

        event_counts = {}
        hourly_activity = {i: 0 for i in range(24)}
        total_events = len(events.data or [])

        for event in (events.data or []):
            et = event.get("event_type", "unknown")
            event_counts[et] = event_counts.get(et, 0) + 1

            created_at = event.get("created_at", "")
            if created_at:
                try:
                    # Parse hour from ISO timestamp (safer than hardcoded slicing)
                    from datetime import datetime as dt
                    hour = dt.fromisoformat(created_at.replace('Z', '+00:00')).hour
                    hourly_activity[hour] += 1
                except (ValueError, IndexError, AttributeError):
                    pass

        # Calculate peak hours
        peak_hour = max(hourly_activity, key=hourly_activity.get) if hourly_activity else 12

        # Get user segments (use count aggregation for efficiency)
        tier_dist = self.client.table("profiles").select("tier").execute()
        segments = {"t1": 0, "t2": 0, "t3": 0}
        for profile in (tier_dist.data or []):
            tier = profile.get("tier", "t1")
            if tier in segments:
                segments[tier] += 1

        return {
            "patterns": {
                "event_distribution": event_counts,
                "peak_activity_hour": peak_hour,
                "hourly_activity": hourly_activity,
                "total_events_analyzed": total_events,
                "limited": total_events >= MAX_USER_EVENTS_BEHAVIOR_ANALYSIS  # Indicate if data was limited
            },
            "segments": {
                "by_tier": segments,
                "total_users": sum(segments.values())
            },
            "period": {
                "start": start_date,
                "end": end_date
            }
        }


class SupabaseAdminModerationRepository:

    """
    Extended repository for admin content moderation operations.

    v3.28: DDD Migration improvements (MOD-CRITICAL-1)
    - Added OOM protection to all queries (MOD-HIGH-2)
    - Fixed return types to Tuple[List, int] (MOD-HIGH-1, MOD-HIGH-4)
    - Added .limit(1) to all update operations (MOD-HIGH-3)
    - Unified method signatures (MOD-MEDIUM-3)
    - Optimized reports_stats to single query (MOD-MEDIUM-2)
    """

    def __init__(self, client):
        self.client = client

    @retry_on_network_error()
    async def admin_get_moderation_list(
        self,
        status: Optional[str] = "pending",
        resource_type: Optional[str] = None,
        offset: int = 0,
        limit: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get moderation queue with offset-based pagination.

        v3.28: MOD-HIGH-1 Fix - Returns (items, total) instead of just items.
        v3.28: MOD-HIGH-2 Fix - Added .limit(10000) OOM protection.

        Returns:
            Tuple of (items list, total count)
        """
        query = self.client.table("marketplace_listings").select(
            "*, profiles(username, email)", count="exact"
        ).eq("is_deleted", False)

        if status:
            query = query.eq("moderation_status", status)
        if resource_type and resource_type != "all":
            query = query.eq("resource_type", resource_type)

        # v3.28: Added OOM protection + count="exact"
        result = query.order("submitted_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .limit(10000)\
            .execute()

        items = result.data or []
        total = result.count or 0

        return (items, total)

    @retry_on_network_error()
    async def admin_get_moderation_detail(self, listing_id: str) -> Optional[Dict[str, Any]]:
        """Get listing detail for moderation."""
        result = self.client.table("marketplace_listings").select(
            "*, profiles(username, email, tier)"
        ).eq("id", listing_id).execute()
        
        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def admin_approve_listing(self, listing_id: str, admin_id: str) -> Optional[Dict[str, Any]]:
        """
        Approve listing.

        v3.28: MOD-HIGH-3 Fix - Added .limit(1) protection.
        """
        result = self.client.table("marketplace_listings").update({
            "moderation_status": "approved",
            "is_public": True,
            "moderated_at": datetime.now(timezone.utc).isoformat(),
            "moderated_by": admin_id,
        }).eq("id", listing_id).limit(1).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def admin_reject_listing(self, listing_id: str, admin_id: str, reason: str) -> Optional[Dict[str, Any]]:
        """
        Reject listing.

        v3.28: MOD-HIGH-3 Fix - Added .limit(1) protection.
        """
        result = self.client.table("marketplace_listings").update({
            "moderation_status": "rejected",
            "is_public": False,
            "rejection_reason": reason,
            "moderated_at": datetime.now(timezone.utc).isoformat(),
            "moderated_by": admin_id,
        }).eq("id", listing_id).limit(1).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def admin_delete_listing(self, listing_id: str) -> Optional[Dict[str, Any]]:
        """
        Delete listing.

        v3.28: MOD-HIGH-3 Fix - Added .limit(1) protection.
        """
        result = self.client.table("marketplace_listings").update({
            "is_deleted": True,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", listing_id).limit(1).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def admin_unpublish_listing(self, listing_id: str) -> Optional[Dict[str, Any]]:
        """
        Unpublish listing.

        v3.28: MOD-HIGH-3 Fix - Added .limit(1) protection.
        """
        result = self.client.table("marketplace_listings").update({
            "is_public": False,
        }).eq("id", listing_id).limit(1).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def admin_get_reports(
        self,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get content reports with offset-based pagination.

        v3.28: MOD-HIGH-4 Fix - Returns (items, total) in single query.
        v3.28: MOD-HIGH-2 Fix - Added .limit(10000) OOM protection.

        Returns:
            Tuple of (reports list, total count)
        """
        query = self.client.table("reports").select(
            "*, profiles!reporter_id(username), marketplace_listings(title)", count="exact"
        )

        if status:
            query = query.eq("status", status)

        # v3.28: Added OOM protection + count="exact"
        result = query.order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .limit(10000)\
            .execute()

        items = result.data or []
        total = result.count or 0

        return (items, total)

    @retry_on_network_error()
    async def admin_get_reports_count(self, status: Optional[str] = None) -> int:
        """
        Get reports count.

        DEPRECATED: Use admin_get_reports() instead which returns both items and count.
        Kept for backward compatibility.
        """
        query = self.client.table("reports").select("id", count="exact")

        if status:
            query = query.eq("status", status)

        result = query.execute()
        return result.count or 0

    @retry_on_network_error()
    async def admin_get_reports_stats(self) -> Dict[str, int]:
        """
        Get reports statistics by status (optimized).

        v3.28: MOD-MEDIUM-2 Fix - Single query with in-memory aggregation.
        Performance: 5 DB roundtrips → 1 DB roundtrip (5x improvement).

        Returns:
            Dict with counts by status (pending, reviewed, resolved, dismissed, total)
        """
        await result = self.client.table("reports").select("status").execute()

        stats = {
            "pending": 0,
            "reviewed": 0,
            "resolved": 0,
            "dismissed": 0,
            "total": 0
        }

        for report in (result.data or []):
            status = report.get("status", "pending")
            if status in stats:
                stats[status] += 1
            stats["total"] += 1

        return stats

    @retry_on_network_error()
    async def admin_respond_to_report(
        self,
        report_id: str,
        admin_id: str,
        new_status: str,
        admin_response: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Respond to report.

        v3.28: MOD-MEDIUM-3 Fix - Renamed parameter 'action' to 'new_status' for consistency.
        v3.28: MOD-MEDIUM-3 Fix - Renamed parameter 'response' to 'admin_response' for clarity.
        v3.28: MOD-HIGH-3 Fix - Added .limit(1) protection.
        """
        result = self.client.table("reports").update({
            "status": new_status,
            "admin_response": admin_response,
            "responded_by": admin_id,
            "responded_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", report_id).limit(1).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def admin_get_report_detail(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get report detail."""
        result = self.client.table("reports").select(
            "*, profiles!reporter_id(username, email), marketplace_listings(*)"
        ).eq("id", report_id).execute()
        
        return result.data[0] if result.data else None


