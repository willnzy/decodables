#!/usr/bin/env python3
"""
Scheduled Data Aggregation Task
定时数据聚合任务

This script should be run periodically (e.g., every hour via cron) to:
1. Pre-compute dashboard statistics
2. Aggregate user behavior data
3. Generate AI insights cache

Usage:
    python aggregate_stats.py              # Run all aggregations
    python aggregate_stats.py --daily      # Run daily aggregations only
    python aggregate_stats.py --hourly     # Run hourly aggregations only

Cron example (run every hour):
    0 * * * * cd /path/to/decodables && python scheduled_tasks/aggregate_stats.py --hourly

Cron example (run daily at 2am):
    0 2 * * * cd /path/to/decodables && python scheduled_tasks/aggregate_stats.py --daily
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client, Client

# Initialize Supabase client
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_KEY environment variables are required")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def log(message):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def aggregate_daily_user_stats():
    """
    Aggregate daily user statistics
    每日用户统计聚合
    """
    log("📊 Starting daily user stats aggregation...")
    
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Calculate stats for each of the last 30 days
    for days_ago in range(30):
        date = today - timedelta(days=days_ago)
        date_str = date.strftime("%Y-%m-%d")
        next_date = date + timedelta(days=1)
        
        # Count new users for this day
        new_users = supabase.table("profiles").select("id", count="exact")\
            .gte("created_at", date.isoformat())\
            .lt("created_at", next_date.isoformat()).execute()
        
        # Count active users (users with activity_logs on this day)
        active_users = supabase.table("activity_logs").select("user_id")\
            .gte("created_at", date.isoformat())\
            .lt("created_at", next_date.isoformat()).execute()
        unique_active = len(set(a.get("user_id") for a in active_users.data or []))
        
        # Count by tier
        tier_counts = {
            "free": 0,
            "starter": 0, 
            "pro": 0
        }
        for tier in tier_counts.keys():
            count = supabase.table("profiles").select("id", count="exact")\
                .eq("tier", tier)\
                .gte("created_at", date.isoformat())\
                .lt("created_at", next_date.isoformat()).execute()
            tier_counts[tier] = count.count or 0
        
        # Upsert to aggregated_stats table
        stats_data = {
            "date": date_str,
            "stat_type": "daily_users",
            "data": {
                "new_users": new_users.count or 0,
                "active_users": unique_active,
                "new_free": tier_counts["free"],
                "new_starter": tier_counts["starter"],
                "new_pro": tier_counts["pro"]
            },
            "updated_at": now.isoformat()
        }
        
        supabase.table("aggregated_stats").upsert(
            stats_data,
            on_conflict="date,stat_type"
        ).execute()
    
    log("✅ Daily user stats aggregation complete")


def aggregate_daily_revenue():
    """
    Aggregate daily revenue statistics
    每日收入统计聚合
    """
    log("💰 Starting daily revenue aggregation...")
    
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    for days_ago in range(30):
        date = today - timedelta(days=days_ago)
        date_str = date.strftime("%Y-%m-%d")
        next_date = date + timedelta(days=1)
        
        # Get payment transactions for this day
        payments = supabase.table("credit_transactions").select("type, description")\
            .eq("bucket", "payment")\
            .gte("created_at", date.isoformat())\
            .lt("created_at", next_date.isoformat()).execute()
        
        subscription_revenue = 0.0
        credits_revenue = 0.0
        
        for tx in payments.data or []:
            tx_type = tx.get("type", "")
            desc = tx.get("description", "")
            
            # Parse amount from description (format: "... | USD 1499")
            amount = 0
            if "|" in desc:
                parts = desc.split("|")[-1].strip().split()
                if len(parts) >= 2:
                    try:
                        amount = int(parts[1]) / 100  # cents to dollars
                    except:
                        pass
            
            if "sub" in tx_type.lower():
                subscription_revenue += amount
            else:
                credits_revenue += amount
        
        stats_data = {
            "date": date_str,
            "stat_type": "daily_revenue",
            "data": {
                "subscriptions": round(subscription_revenue, 2),
                "credits": round(credits_revenue, 2),
                "total": round(subscription_revenue + credits_revenue, 2)
            },
            "updated_at": now.isoformat()
        }
        
        supabase.table("aggregated_stats").upsert(
            stats_data,
            on_conflict="date,stat_type"
        ).execute()
    
    log("✅ Daily revenue aggregation complete")


def aggregate_daily_projects():
    """
    Aggregate daily project statistics
    每日项目统计聚合
    """
    log("📁 Starting daily projects aggregation...")
    
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    for days_ago in range(30):
        date = today - timedelta(days=days_ago)
        date_str = date.strftime("%Y-%m-%d")
        next_date = date + timedelta(days=1)
        
        # Count projects created this day
        created = supabase.table("projects").select("id", count="exact")\
            .gte("created_at", date.isoformat())\
            .lt("created_at", next_date.isoformat()).execute()
        
        # Count completed projects (have cover_url)
        completed = supabase.table("projects").select("id", count="exact")\
            .gte("created_at", date.isoformat())\
            .lt("created_at", next_date.isoformat())\
            .not_.is_("cover_url", "null").execute()
        
        # Count exports from activity_logs
        exports = supabase.table("activity_logs").select("action")\
            .in_("action", ["export_pdf", "export_zip"])\
            .gte("created_at", date.isoformat())\
            .lt("created_at", next_date.isoformat()).execute()
        
        stats_data = {
            "date": date_str,
            "stat_type": "daily_projects",
            "data": {
                "created": created.count or 0,
                "completed": completed.count or 0,
                "exported": len(exports.data or [])
            },
            "updated_at": now.isoformat()
        }
        
        supabase.table("aggregated_stats").upsert(
            stats_data,
            on_conflict="date,stat_type"
        ).execute()
    
    log("✅ Daily projects aggregation complete")


def aggregate_credit_usage():
    """
    Aggregate credit usage by type
    积分使用统计聚合
    """
    log("⚡ Starting credit usage aggregation...")
    
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=30)).isoformat()
    
    # Get all credit-consuming transactions
    transactions = supabase.table("credit_transactions").select("type, amount")\
        .lt("amount", 0)\
        .gte("created_at", start_date).execute()
    
    usage_by_type = defaultdict(int)
    type_labels = {
        "generation": "Image Generation",
        "text_generation": "Text Generation",
        "ocr": "OCR Scan",
        "market_purchase": "Marketplace",
        "export_pdf": "PDF Export",
        "export_zip": "ZIP Export"
    }
    
    for tx in transactions.data or []:
        tx_type = tx.get("type", "other")
        amount = abs(tx.get("amount", 0))
        label = type_labels.get(tx_type, tx_type.replace("_", " ").title())
        usage_by_type[label] += amount
    
    stats_data = {
        "date": now.strftime("%Y-%m-%d"),
        "stat_type": "credit_usage_30d",
        "data": dict(usage_by_type),
        "updated_at": now.isoformat()
    }
    
    supabase.table("aggregated_stats").upsert(
        stats_data,
        on_conflict="date,stat_type"
    ).execute()
    
    log("✅ Credit usage aggregation complete")


def aggregate_tier_distribution():
    """
    Aggregate user tier distribution
    用户等级分布聚合
    """
    log("👥 Starting tier distribution aggregation...")
    
    now = datetime.now(timezone.utc)
    
    free_count = supabase.table("profiles").select("id", count="exact").eq("tier", "free").execute()
    starter_count = supabase.table("profiles").select("id", count="exact").eq("tier", "starter").execute()
    pro_count = supabase.table("profiles").select("id", count="exact").eq("tier", "pro").execute()
    
    stats_data = {
        "date": now.strftime("%Y-%m-%d"),
        "stat_type": "tier_distribution",
        "data": {
            "free": free_count.count or 0,
            "starter": starter_count.count or 0,
            "pro": pro_count.count or 0
        },
        "updated_at": now.isoformat()
    }
    
    supabase.table("aggregated_stats").upsert(
        stats_data,
        on_conflict="date,stat_type"
    ).execute()
    
    log("✅ Tier distribution aggregation complete")


def aggregate_conversion_funnel():
    """
    Aggregate conversion funnel data
    转化漏斗聚合
    """
    log("📈 Starting conversion funnel aggregation...")
    
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=30)).isoformat()
    
    # Total signups in last 30 days
    signups = supabase.table("profiles").select("id", count="exact")\
        .gte("created_at", start_date).execute()
    
    # Users who created projects
    project_users = supabase.table("projects").select("user_id")\
        .gte("created_at", start_date).execute()
    unique_project_users = len(set(p.get("user_id") for p in project_users.data or []))
    
    # Users who paid
    paid_users = supabase.table("credit_transactions").select("user_id")\
        .eq("bucket", "payment")\
        .gte("created_at", start_date).execute()
    unique_paid_users = len(set(p.get("user_id") for p in paid_users.data or []))
    
    # Active subscribers
    active_subs = supabase.table("profiles").select("id", count="exact")\
        .in_("tier", ["starter", "pro"])\
        .eq("subscription_status", "active").execute()
    
    # Estimate visitors (signups * 4)
    visitors = (signups.count or 0) * 4
    
    stats_data = {
        "date": now.strftime("%Y-%m-%d"),
        "stat_type": "conversion_funnel_30d",
        "data": {
            "visitors": visitors,
            "signups": signups.count or 0,
            "first_project": unique_project_users,
            "paid_users": unique_paid_users,
            "active_subscribers": active_subs.count or 0
        },
        "updated_at": now.isoformat()
    }
    
    supabase.table("aggregated_stats").upsert(
        stats_data,
        on_conflict="date,stat_type"
    ).execute()
    
    log("✅ Conversion funnel aggregation complete")


def aggregate_event_stats():
    """
    Aggregate user event statistics
    用户事件统计聚合
    """
    log("📊 Starting event stats aggregation...")
    
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=7)).isoformat()
    
    # Get event counts by type
    events = supabase.table("user_events").select("event_type")\
        .gte("created_at", start_date).execute()
    
    event_counts = defaultdict(int)
    for event in events.data or []:
        event_type = event.get("event_type", "unknown")
        event_counts[event_type] += 1
    
    stats_data = {
        "date": now.strftime("%Y-%m-%d"),
        "stat_type": "event_stats_7d",
        "data": dict(event_counts),
        "updated_at": now.isoformat()
    }
    
    supabase.table("aggregated_stats").upsert(
        stats_data,
        on_conflict="date,stat_type"
    ).execute()
    
    log("✅ Event stats aggregation complete")


def run_hourly_tasks():
    """Run tasks that should be executed hourly"""
    log("🕐 Running hourly aggregation tasks...")
    
    aggregate_tier_distribution()
    aggregate_event_stats()
    
    log("✅ Hourly tasks complete")


def run_daily_tasks():
    """Run tasks that should be executed daily"""
    log("📅 Running daily aggregation tasks...")
    
    aggregate_daily_user_stats()
    aggregate_daily_revenue()
    aggregate_daily_projects()
    aggregate_credit_usage()
    aggregate_conversion_funnel()
    
    log("✅ Daily tasks complete")


def run_all_tasks():
    """Run all aggregation tasks"""
    log("🚀 Running all aggregation tasks...")
    
    run_daily_tasks()
    run_hourly_tasks()
    
    log("🎉 All tasks complete!")


def main():
    parser = argparse.ArgumentParser(description="Run scheduled data aggregation tasks")
    parser.add_argument("--hourly", action="store_true", help="Run hourly tasks only")
    parser.add_argument("--daily", action="store_true", help="Run daily tasks only")
    args = parser.parse_args()
    
    if args.hourly:
        run_hourly_tasks()
    elif args.daily:
        run_daily_tasks()
    else:
        run_all_tasks()


if __name__ == "__main__":
    main()

