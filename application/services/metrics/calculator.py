"""
Metrics Calculator - Core SaaS metrics calculation

@module scheduled_tasks.metrics_etl.calculator
@version 3.24
"""

from datetime import datetime, timedelta, timezone, date
from typing import Dict, List, Optional
from collections import defaultdict
from decimal import Decimal

from .utils import get_supabase, log, is_bot, get_utc_date_range, TIER_PRICING, RETENTION_DAYS


class MetricsCalculator:
    """Core SaaS metrics calculator with proper methodology."""
    
    def __init__(self):
        self.supabase = get_supabase()
    
    def calculate_dau(self, target_date: date) -> int:
        """Calculate Daily Active Users using hybrid identification."""
        start_ts, end_ts = get_utc_date_range(target_date)
        
        result = self.supabase.table("analytics_events").select(
            "user_id, session_id, context"
        ).gte("created_at", start_ts).lt("created_at", end_ts).execute()
        
        unique_users = set()
        
        for event in result.data or []:
            context = event.get("context", {}) or {}
            user_agent = context.get("user_agent", "")
            if is_bot(user_agent):
                continue
            
            user_id = event.get("user_id")
            session_id = event.get("session_id")
            
            if user_id:
                unique_users.add(f"user:{user_id}")
            elif session_id:
                unique_users.add(f"session:{session_id}")
        
        return len(unique_users)
    
    def calculate_wau(self, end_date: date) -> int:
        """Calculate Weekly Active Users (7-day window)."""
        start = end_date - timedelta(days=7)
        start_ts = datetime.combine(start, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
        end_ts = datetime.combine(end_date + timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
        
        result = self.supabase.table("analytics_events").select(
            "user_id, session_id, context"
        ).gte("created_at", start_ts).lt("created_at", end_ts).execute()
        
        unique_users = set()
        for event in result.data or []:
            context = event.get("context", {}) or {}
            if is_bot(context.get("user_agent", "")):
                continue
            user_id = event.get("user_id")
            if user_id:
                unique_users.add(user_id)
            elif event.get("session_id"):
                unique_users.add(f"s:{event['session_id']}")
        
        return len(unique_users)
    
    def calculate_mau(self, end_date: date) -> int:
        """Calculate Monthly Active Users (30-day window)."""
        start = end_date - timedelta(days=30)
        start_ts = datetime.combine(start, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
        end_ts = datetime.combine(end_date + timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
        
        result = self.supabase.table("analytics_events").select(
            "user_id, session_id, context"
        ).gte("created_at", start_ts).lt("created_at", end_ts).limit(10000).execute()
        
        unique_users = set()
        for event in result.data or []:
            context = event.get("context", {}) or {}
            if is_bot(context.get("user_agent", "")):
                continue
            user_id = event.get("user_id")
            if user_id:
                unique_users.add(user_id)
            elif event.get("session_id"):
                unique_users.add(f"s:{event['session_id']}")
        
        return len(unique_users)
    
    def calculate_new_users(self, target_date: date) -> Dict:
        """Calculate new user signups by tier."""
        start_ts, end_ts = get_utc_date_range(target_date)
        
        result = self.supabase.table("profiles").select("id, tier")\
            .gte("created_at", start_ts).lt("created_at", end_ts).execute()
        
        by_tier = defaultdict(int)
        for user in result.data or []:
            tier = user.get("tier", "t1")
            by_tier[tier] += 1
        
        return {
            "total": len(result.data or []),
            "t1": by_tier.get("t1", 0),
            "t2": by_tier.get("t2", 0),
            "t3": by_tier.get("t3", 0),
        }
    
    def calculate_mrr(self, target_date: date) -> Dict:
        """Calculate Monthly Recurring Revenue."""
        result = self.supabase.table("profiles").select("tier, subscription_status")\
            .eq("subscription_status", "active").execute()
        
        mrr_by_tier = defaultdict(Decimal)
        subscriber_count = defaultdict(int)
        
        for user in result.data or []:
            tier = user.get("tier", "t1")
            if tier in TIER_PRICING:
                mrr_by_tier[tier] += Decimal(TIER_PRICING[tier]) / 100
                subscriber_count[tier] += 1
        
        total_mrr = sum(mrr_by_tier.values())
        
        return {
            "total": float(total_mrr),
            "by_tier": {k: float(v) for k, v in mrr_by_tier.items()},
            "subscribers": dict(subscriber_count),
        }
    
    def calculate_arpu(self, target_date: date) -> float:
        """Calculate Average Revenue Per User."""
        mrr_data = self.calculate_mrr(target_date)
        mau = self.calculate_mau(target_date)
        
        if mau == 0:
            return 0.0
        
        return round(mrr_data["total"] / mau, 2)
    
    def calculate_retention(self, cohort_date: date) -> Dict:
        """Calculate cohort retention rates."""
        cohort_start, cohort_end = get_utc_date_range(cohort_date)
        
        # Get cohort users
        cohort = self.supabase.table("profiles").select("id")\
            .gte("created_at", cohort_start).lt("created_at", cohort_end).execute()
        
        cohort_ids = [u["id"] for u in (cohort.data or [])]
        if not cohort_ids:
            return {"cohort_size": 0, "retention": {}}
        
        retention_rates = {}
        now = datetime.now(timezone.utc).date()
        
        for day in RETENTION_DAYS:
            check_date = cohort_date + timedelta(days=day)
            if check_date > now:
                continue
            
            check_start, check_end = get_utc_date_range(check_date)
            
            # Check for activity
            sample = cohort_ids[:100]  # Sample for performance
            active = self.supabase.table("analytics_events").select("user_id")\
                .in_("user_id", sample)\
                .gte("created_at", check_start).lt("created_at", check_end).execute()
            
            active_ids = set(e["user_id"] for e in (active.data or []))
            rate = len(active_ids) / len(sample) * 100 if sample else 0
            retention_rates[f"day_{day}"] = round(rate, 1)
        
        return {
            "cohort_size": len(cohort_ids),
            "retention": retention_rates,
        }
    
    def calculate_conversion_rate(self, target_date: date) -> Dict:
        """Calculate conversion funnel rates."""
        end_ts = datetime.combine(target_date + timedelta(days=1), 
                                   datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
        
        # Total signups
        signups = self.supabase.table("profiles").select("id", count="exact")\
            .lte("created_at", end_ts).execute()
        
        # Converted to paid
        paid = self.supabase.table("profiles").select("id", count="exact")\
            .neq("tier", "t1").eq("subscription_status", "active")\
            .lte("created_at", end_ts).execute()
        
        total = signups.count or 1
        converted = paid.count or 0
        
        return {
            "signups": total,
            "converted": converted,
            "rate": round(converted / total * 100, 2),
        }
