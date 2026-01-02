#!/usr/bin/env python3
"""
Metrics ETL Service (v3.12)

Industry-standard SaaS metrics calculation and aggregation.
This module replaces the legacy aggregate_stats.py with proper:
- Hybrid user identification (user_id + session_id for anonymous)
- Bot filtering
- Cohort-based retention analysis
- Proper MRR/ARPU calculation
- UTC-standardized time handling

Usage:
    python scheduled_tasks/metrics_etl.py --daily    # Run daily aggregation
    python scheduled_tasks/metrics_etl.py --hourly   # Run hourly quick stats
    python scheduled_tasks/metrics_etl.py --backfill 30  # Backfill last 30 days
"""

import os
import sys
import json
import argparse
import re
from datetime import datetime, timedelta, timezone, date
from typing import Optional, Dict, Any, List, Tuple
from collections import defaultdict
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from db_service import supabase

if supabase is None:
    print("❌ Error: Supabase client not initialized")
    sys.exit(1)


# ==========================================
# Configuration
# ==========================================

# Bot User-Agent patterns to filter
BOT_PATTERNS = re.compile(
    r'bot|crawler|spider|scraper|headless|phantom|selenium|puppeteer|playwright|'
    r'googlebot|bingbot|slurp|duckduckbot|baiduspider|yandexbot|facebookexternalhit|'
    r'twitterbot|linkedinbot|whatsapp|telegram|discord|slack',
    re.IGNORECASE
)

# Subscription pricing (cents)
TIER_PRICING = {
    'starter': 999,    # $9.99/month
    'pro': 2499,       # $24.99/month
}

# Retention periods to calculate
RETENTION_DAYS = [1, 7, 14, 30, 60, 90]


# ==========================================
# Utility Functions
# ==========================================

def log(message: str, level: str = "INFO"):
    """Structured logging with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def is_bot(user_agent: Optional[str]) -> bool:
    """Check if user agent indicates a bot"""
    if not user_agent:
        return False
    return bool(BOT_PATTERNS.search(user_agent))


def get_utc_date_range(target_date: date) -> Tuple[str, str]:
    """Get UTC timestamp range for a date"""
    start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()


# ==========================================
# Core Metric Calculators
# ==========================================

class MetricsCalculator:
    """Core SaaS metrics calculator with proper methodology"""
    
    def __init__(self):
        self.supabase = supabase
    
    def calculate_dau(self, target_date: date) -> int:
        """
        Calculate Daily Active Users using hybrid identification.
        - Logged-in users: count by user_id
        - Anonymous users: count by session_id
        - Filters out bots
        """
        start_ts, end_ts = get_utc_date_range(target_date)
        
        # Get all events for the day
        result = self.supabase.table("analytics_events").select(
            "user_id, session_id, context"
        ).gte("created_at", start_ts).lt("created_at", end_ts).execute()
        
        unique_users = set()
        
        for event in result.data or []:
            # Filter bots
            context = event.get("context", {}) or {}
            user_agent = context.get("user_agent", "")
            if is_bot(user_agent):
                continue
            
            # Hybrid ID: prefer user_id, fallback to session_id
            user_id = event.get("user_id")
            session_id = event.get("session_id")
            
            if user_id:
                unique_users.add(f"user:{user_id}")
            elif session_id:
                unique_users.add(f"session:{session_id}")
        
        return len(unique_users)
    
    def calculate_mau(self, target_month: date) -> int:
        """
        Calculate Monthly Active Users.
        Same hybrid identification as DAU.
        """
        month_start = target_month.replace(day=1)
        if target_month.month == 12:
            month_end = target_month.replace(year=target_month.year + 1, month=1, day=1)
        else:
            month_end = target_month.replace(month=target_month.month + 1, day=1)
        
        start_ts = datetime.combine(month_start, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
        end_ts = datetime.combine(month_end, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
        
        # Paginate through events (MAU can be large)
        unique_users = set()
        offset = 0
        batch_size = 5000
        
        while True:
            result = self.supabase.table("analytics_events").select(
                "user_id, session_id, context"
            ).gte("created_at", start_ts).lt("created_at", end_ts).range(offset, offset + batch_size - 1).execute()
            
            if not result.data:
                break
            
            for event in result.data:
                context = event.get("context", {}) or {}
                if is_bot(context.get("user_agent", "")):
                    continue
                
                user_id = event.get("user_id")
                session_id = event.get("session_id")
                
                if user_id:
                    unique_users.add(f"user:{user_id}")
                elif session_id:
                    unique_users.add(f"session:{session_id}")
            
            if len(result.data) < batch_size:
                break
            offset += batch_size
        
        return len(unique_users)
    
    def calculate_mrr(self) -> int:
        """
        Calculate Monthly Recurring Revenue (in cents).
        Sum of active subscription values.
        """
        result = self.supabase.table("profiles").select(
            "tier"
        ).in_("tier", ["starter", "pro"]).eq("subscription_status", "active").execute()
        
        mrr_cents = 0
        for profile in result.data or []:
            tier = profile.get("tier", "")
            mrr_cents += TIER_PRICING.get(tier, 0)
        
        return mrr_cents
    
    def calculate_arpu(self, mau: int, mrr_cents: int) -> int:
        """Calculate Average Revenue Per User (in cents)"""
        if mau <= 0:
            return 0
        return mrr_cents // mau
    
    def calculate_cohort_retention(self, cohort_start: date, cohort_end: date, retention_day: int) -> Dict[str, Any]:
        """
        Calculate retention rate for a cohort.
        
        Args:
            cohort_start: Start date of cohort
            cohort_end: End date of cohort (exclusive)
            retention_day: Which day to check retention (1, 7, 14, 30, etc.)
        
        Returns:
            {cohort_size, retained_count, retention_rate}
        """
        # Get users who signed up in the cohort period
        cohort_start_ts = datetime.combine(cohort_start, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
        cohort_end_ts = datetime.combine(cohort_end, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
        
        cohort_users = self.supabase.table("profiles").select("id").gte(
            "created_at", cohort_start_ts
        ).lt("created_at", cohort_end_ts).execute()
        
        user_ids = [u["id"] for u in cohort_users.data or []]
        cohort_size = len(user_ids)
        
        if cohort_size == 0:
            return {"cohort_size": 0, "retained_count": 0, "retention_rate": 0.0}
        
        # Check activity on retention day
        check_date = cohort_start + timedelta(days=retention_day)
        check_start_ts, check_end_ts = get_utc_date_range(check_date)
        
        # Query in batches to avoid timeout
        retained_users = set()
        batch_size = 100
        
        for i in range(0, len(user_ids), batch_size):
            batch_ids = user_ids[i:i + batch_size]
            
            activity = self.supabase.table("analytics_events").select(
                "user_id"
            ).in_("user_id", batch_ids).gte(
                "created_at", check_start_ts
            ).lt("created_at", check_end_ts).execute()
            
            for event in activity.data or []:
                if event.get("user_id"):
                    retained_users.add(event["user_id"])
        
        retained_count = len(retained_users)
        retention_rate = round((retained_count / cohort_size) * 100, 2)
        
        return {
            "cohort_size": cohort_size,
            "retained_count": retained_count,
            "retention_rate": retention_rate
        }
    
    def calculate_funnel(self, target_date: date) -> Dict[str, int]:
        """
        Calculate conversion funnel metrics.
        
        Stages:
        1. Visitors - Unique sessions with page_view
        2. Signups - New registrations
        3. Activated - Users who created first project
        4. Engaged - Users with 3+ sessions in 7 days
        5. Converted - Made first payment
        """
        start_ts, end_ts = get_utc_date_range(target_date)
        
        funnel = {
            "visitors": 0,
            "signups": 0,
            "activated": 0,
            "engaged": 0,
            "converted": 0,
        }
        
        # Visitors: unique sessions with page_view
        visitors = self.supabase.table("analytics_events").select(
            "session_id, context"
        ).eq("event_name", "page_view").gte(
            "created_at", start_ts
        ).lt("created_at", end_ts).execute()
        
        unique_sessions = set()
        for v in visitors.data or []:
            context = v.get("context", {}) or {}
            if not is_bot(context.get("user_agent", "")):
                if v.get("session_id"):
                    unique_sessions.add(v["session_id"])
        funnel["visitors"] = len(unique_sessions)
        
        # Signups: new profiles created
        signups = self.supabase.table("profiles").select(
            "id", count="exact"
        ).gte("created_at", start_ts).lt("created_at", end_ts).execute()
        funnel["signups"] = signups.count or 0
        
        # Activated: users who created their first project on this day
        # (Approximation: projects created by new users)
        new_user_ids = [p["id"] for p in signups.data or []]
        if new_user_ids:
            projects = self.supabase.table("projects").select(
                "user_id"
            ).in_("user_id", new_user_ids[:100]).gte(
                "created_at", start_ts
            ).lt("created_at", end_ts).eq("is_deleted", False).execute()
            funnel["activated"] = len(set(p["user_id"] for p in projects.data or []))
        
        # Converted: users who made first payment (from credit_transactions)
        payments = self.supabase.table("credit_transactions").select(
            "user_id"
        ).eq("bucket", "payment").gte(
            "created_at", start_ts
        ).lt("created_at", end_ts).execute()
        funnel["converted"] = len(set(p["user_id"] for p in payments.data or []))
        
        return funnel
    
    def calculate_ai_metrics(self, target_date: date) -> Dict[str, Any]:
        """Calculate AI generation metrics"""
        start_ts, end_ts = get_utc_date_range(target_date)
        
        # Get AI generation events
        events = self.supabase.table("analytics_events").select(
            "event_name, properties"
        ).in_("event_name", [
            "ai_generate_started", "ai_generation_start",
            "ai_generate_success", "ai_generation_complete",
            "ai_generate_failed", "ai_generation_failed"
        ]).gte("created_at", start_ts).lt("created_at", end_ts).execute()
        
        started = 0
        succeeded = 0
        failed = 0
        
        for event in events.data or []:
            name = event.get("event_name", "")
            if "start" in name.lower():
                started += 1
            elif "success" in name.lower() or "complete" in name.lower():
                succeeded += 1
            elif "fail" in name.lower():
                failed += 1
        
        success_rate = round((succeeded / started * 100), 2) if started > 0 else 0.0
        
        return {
            "total_generations": started,
            "successful": succeeded,
            "failed": failed,
            "success_rate": success_rate
        }


# ==========================================
# ETL Aggregation Jobs
# ==========================================

class MetricsETL:
    """ETL job runner for metrics aggregation"""
    
    def __init__(self):
        self.calculator = MetricsCalculator()
    
    def aggregate_daily_metrics(self, target_date: date):
        """
        Main daily aggregation job.
        Should run at 2 AM UTC to aggregate previous day's data.
        """
        log(f"📊 Aggregating daily metrics for {target_date}")
        
        start_ts, end_ts = get_utc_date_range(target_date)
        
        # Calculate all metrics
        dau = self.calculator.calculate_dau(target_date)
        log(f"  DAU: {dau}")
        
        # New users by tier
        new_users_result = supabase.table("profiles").select(
            "tier", count="exact"
        ).gte("created_at", start_ts).lt("created_at", end_ts).execute()
        
        tier_counts = defaultdict(int)
        for profile in new_users_result.data or []:
            tier_counts[profile.get("tier", "free")] += 1
        
        log(f"  New users: {new_users_result.count or 0} (free={tier_counts['free']}, starter={tier_counts['starter']}, pro={tier_counts['pro']})")
        
        # Session count
        sessions = supabase.table("analytics_events").select(
            "session_id"
        ).gte("created_at", start_ts).lt("created_at", end_ts).execute()
        unique_sessions = len(set(s.get("session_id") for s in sessions.data or [] if s.get("session_id")))
        log(f"  Sessions: {unique_sessions}")
        
        # Event counts
        events = supabase.table("analytics_events").select(
            "event_name", count="exact"
        ).gte("created_at", start_ts).lt("created_at", end_ts).execute()
        total_events = events.count or 0
        
        # Page views
        page_views = supabase.table("analytics_events").select(
            "id", count="exact"
        ).eq("event_name", "page_view").gte(
            "created_at", start_ts
        ).lt("created_at", end_ts).execute()
        
        # AI metrics
        ai_metrics = self.calculator.calculate_ai_metrics(target_date)
        log(f"  AI: {ai_metrics['total_generations']} generations, {ai_metrics['success_rate']}% success rate")
        
        # Project counts
        projects_created = supabase.table("projects").select(
            "id", count="exact"
        ).gte("created_at", start_ts).lt("created_at", end_ts).eq("is_deleted", False).execute()
        
        # Export events
        exports = supabase.table("analytics_events").select(
            "id", count="exact"
        ).in_("event_name", [
            "project_exported", "project_export_pdf", "project_export_zip"
        ]).gte("created_at", start_ts).lt("created_at", end_ts).execute()
        
        # Error count
        errors = supabase.table("error_logs").select(
            "id", count="exact"
        ).gte("created_at", start_ts).lt("created_at", end_ts).execute()
        
        # Upsert to analytics_daily_metrics
        metrics_data = {
            "metric_date": target_date.isoformat(),
            "dau": dau,
            "new_users": new_users_result.count or 0,
            "new_free": tier_counts["free"],
            "new_starter": tier_counts["starter"],
            "new_pro": tier_counts["pro"],
            "total_sessions": unique_sessions,
            "total_events": total_events,
            "total_page_views": page_views.count or 0,
            "ai_generations": ai_metrics["total_generations"],
            "ai_success_rate": ai_metrics["success_rate"],
            "projects_created": projects_created.count or 0,
            "projects_exported": exports.count or 0,
            "error_count": errors.count or 0,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("analytics_daily_metrics").upsert(
            metrics_data,
            on_conflict="metric_date"
        ).execute()
        
        log(f"✅ Daily metrics aggregated for {target_date}")
        
        return metrics_data
    
    def aggregate_error_summary(self, target_date: date):
        """Aggregate error statistics for monitoring dashboard"""
        log(f"🚨 Aggregating error summary for {target_date}")
        
        start_ts, end_ts = get_utc_date_range(target_date)
        
        # Get all errors for the day
        errors = supabase.table("error_logs").select(
            "error_code, error_type, endpoint, message, user_id, session_id, context"
        ).gte("created_at", start_ts).lt("created_at", end_ts).execute()
        
        # Group by error_code, error_type, endpoint
        error_groups = defaultdict(lambda: {
            "count": 0,
            "users": set(),
            "sessions": set(),
            "messages": [],
            "request_ids": []
        })
        
        for error in errors.data or []:
            key = (
                error.get("error_code") or "UNKNOWN",
                error.get("error_type") or "OTHER",
                error.get("endpoint") or ""
            )
            group = error_groups[key]
            group["count"] += 1
            
            if error.get("user_id"):
                group["users"].add(error["user_id"])
            if error.get("session_id"):
                group["sessions"].add(error["session_id"])
            if error.get("message"):
                group["messages"].append(error["message"])
            
            context = error.get("context", {}) or {}
            if context.get("request_id"):
                group["request_ids"].append(context["request_id"])
        
        # Insert summaries
        for (error_code, error_type, endpoint), data in error_groups.items():
            summary_data = {
                "summary_date": target_date.isoformat(),
                "error_code": error_code,
                "error_type": error_type,
                "endpoint": endpoint or None,
                "occurrence_count": data["count"],
                "affected_users": len(data["users"]),
                "affected_sessions": len(data["sessions"]),
                "sample_message": data["messages"][0] if data["messages"] else None,
                "sample_request_id": data["request_ids"][0] if data["request_ids"] else None,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Upsert
            supabase.table("analytics_error_summary").upsert(
                summary_data,
                on_conflict="summary_date,error_code,error_type,endpoint"
            ).execute()
        
        log(f"✅ Error summary aggregated: {len(error_groups)} unique error types")
    
    def aggregate_cohort_retention(self):
        """Update cohort retention metrics"""
        log("📈 Aggregating cohort retention...")
        
        today = date.today()
        
        # Process weekly cohorts for last 90 days
        for weeks_ago in range(13):  # ~90 days
            cohort_start = today - timedelta(weeks=weeks_ago + 1)
            cohort_start = cohort_start - timedelta(days=cohort_start.weekday())  # Start of week
            cohort_end = cohort_start + timedelta(days=7)
            
            # Skip if cohort is in the future
            if cohort_start >= today:
                continue
            
            cohort_data = {
                "cohort_date": cohort_start.isoformat(),
                "cohort_type": "week",
                "cohort_size": 0,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Calculate retention for each period
            for day in RETENTION_DAYS:
                # Skip if retention day hasn't happened yet
                if cohort_start + timedelta(days=day) > today:
                    continue
                
                result = self.calculator.calculate_cohort_retention(
                    cohort_start, cohort_end, day
                )
                
                cohort_data["cohort_size"] = result["cohort_size"]
                cohort_data[f"retained_d{day}"] = result["retained_count"]
                cohort_data[f"rate_d{day}"] = result["retention_rate"]
            
            if cohort_data["cohort_size"] > 0:
                supabase.table("analytics_cohort_retention").upsert(
                    cohort_data,
                    on_conflict="cohort_date,cohort_type"
                ).execute()
                log(f"  Week {cohort_start}: {cohort_data['cohort_size']} users, D1={cohort_data.get('rate_d1', 0)}%")
        
        log("✅ Cohort retention aggregated")
    
    def aggregate_funnel_metrics(self, target_date: date):
        """Aggregate conversion funnel for the day"""
        log(f"🔽 Aggregating funnel metrics for {target_date}")
        
        funnel = self.calculator.calculate_funnel(target_date)
        
        # Calculate rates
        rates = {}
        if funnel["visitors"] > 0:
            rates["rate_visitor_signup"] = round(funnel["signups"] / funnel["visitors"] * 100, 2)
        if funnel["signups"] > 0:
            rates["rate_signup_activated"] = round(funnel["activated"] / funnel["signups"] * 100, 2)
        if funnel["visitors"] > 0:
            rates["rate_visitor_converted"] = round(funnel["converted"] / funnel["visitors"] * 100, 2)
        
        funnel_data = {
            "metric_date": target_date.isoformat(),
            "funnel_type": "main",
            "stage_visitors": funnel["visitors"],
            "stage_signups": funnel["signups"],
            "stage_activated": funnel["activated"],
            "stage_engaged": funnel.get("engaged", 0),
            "stage_converted": funnel["converted"],
            **rates,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("analytics_funnel_metrics").upsert(
            funnel_data,
            on_conflict="metric_date,funnel_type"
        ).execute()
        
        log(f"✅ Funnel: {funnel['visitors']} visitors → {funnel['signups']} signups → {funnel['converted']} converted")
    
    def aggregate_monthly_metrics(self, target_month: date):
        """Aggregate monthly metrics (run on 1st of each month for previous month)"""
        log(f"📅 Aggregating monthly metrics for {target_month.strftime('%Y-%m')}")
        
        month_start = target_month.replace(day=1)
        
        # MAU
        mau = self.calculator.calculate_mau(month_start)
        log(f"  MAU: {mau}")
        
        # MRR (current, not historical)
        mrr_cents = self.calculator.calculate_mrr()
        arpu_cents = self.calculator.calculate_arpu(mau, mrr_cents)
        log(f"  MRR: ${mrr_cents / 100:.2f}, ARPU: ${arpu_cents / 100:.2f}")
        
        # Subscriber counts
        active_subs = supabase.table("profiles").select(
            "id", count="exact"
        ).in_("tier", ["starter", "pro"]).eq("subscription_status", "active").execute()
        
        # Get daily metrics for the month to calculate averages
        month_end = (month_start + timedelta(days=32)).replace(day=1)
        daily_metrics = supabase.table("analytics_daily_metrics").select(
            "dau, total_sessions, total_events"
        ).gte("metric_date", month_start.isoformat()).lt(
            "metric_date", month_end.isoformat()
        ).execute()
        
        avg_dau = 0
        total_sessions = 0
        total_events = 0
        
        if daily_metrics.data:
            dau_values = [d.get("dau", 0) for d in daily_metrics.data]
            avg_dau = sum(dau_values) // len(dau_values) if dau_values else 0
            total_sessions = sum(d.get("total_sessions", 0) for d in daily_metrics.data)
            total_events = sum(d.get("total_events", 0) for d in daily_metrics.data)
        
        monthly_data = {
            "metric_month": month_start.isoformat(),
            "mau": mau,
            "mrr_cents": mrr_cents,
            "arr_cents": mrr_cents * 12,
            "arpu_cents": arpu_cents,
            "active_subscribers": active_subs.count or 0,
            "avg_dau": avg_dau,
            "total_sessions": total_sessions,
            "total_events": total_events,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("analytics_monthly_metrics").upsert(
            monthly_data,
            on_conflict="metric_month"
        ).execute()
        
        log(f"✅ Monthly metrics aggregated for {target_month.strftime('%Y-%m')}")


# ==========================================
# Job Runners
# ==========================================

def run_daily_etl():
    """Run daily ETL job (should run at 2 AM UTC)"""
    log("🚀 Starting daily ETL job")
    
    etl = MetricsETL()
    yesterday = date.today() - timedelta(days=1)
    
    # Core daily metrics
    etl.aggregate_daily_metrics(yesterday)
    
    # Error summary
    etl.aggregate_error_summary(yesterday)
    
    # Funnel metrics
    etl.aggregate_funnel_metrics(yesterday)
    
    # Cohort retention (weekly)
    etl.aggregate_cohort_retention()
    
    # Monthly metrics (on 1st of month)
    if date.today().day == 1:
        last_month = date.today() - timedelta(days=1)
        etl.aggregate_monthly_metrics(last_month)
    
    log("🎉 Daily ETL complete!")


def run_hourly_etl():
    """Run hourly quick stats (lightweight)"""
    log("⏰ Starting hourly ETL job")
    
    etl = MetricsETL()
    today = date.today()
    
    # Update today's metrics (partial day)
    etl.aggregate_daily_metrics(today)
    
    log("✅ Hourly ETL complete!")


def backfill_metrics(days: int):
    """Backfill historical metrics"""
    log(f"🔄 Backfilling metrics for last {days} days")
    
    etl = MetricsETL()
    today = date.today()
    
    for i in range(days, 0, -1):
        target_date = today - timedelta(days=i)
        log(f"\n--- Processing {target_date} ---")
        
        etl.aggregate_daily_metrics(target_date)
        etl.aggregate_error_summary(target_date)
        etl.aggregate_funnel_metrics(target_date)
    
    # Update cohort retention
    etl.aggregate_cohort_retention()
    
    log(f"\n🎉 Backfill complete for {days} days!")


def main():
    parser = argparse.ArgumentParser(description="SaaS Metrics ETL Service")
    parser.add_argument("--daily", action="store_true", help="Run daily aggregation")
    parser.add_argument("--hourly", action="store_true", help="Run hourly quick stats")
    parser.add_argument("--backfill", type=int, metavar="DAYS", help="Backfill last N days")
    args = parser.parse_args()
    
    if args.backfill:
        backfill_metrics(args.backfill)
    elif args.hourly:
        run_hourly_etl()
    elif args.daily:
        run_daily_etl()
    else:
        # Default: run daily
        run_daily_etl()


if __name__ == "__main__":
    main()
