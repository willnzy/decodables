#!/usr/bin/env python3
"""
Scheduled Data Aggregation Task
定时数据聚合任务

This script should be run periodically (e.g., every hour via cron) to:
1. Pre-compute dashboard statistics
2. Aggregate user behavior data
3. Generate AI insights cache

Usage:
    python scheduled_tasks/aggregate_stats.py              # Run all aggregations
    python scheduled_tasks/aggregate_stats.py --daily      # Run daily aggregations only
    python scheduled_tasks/aggregate_stats.py --hourly     # Run hourly aggregations only

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

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import supabase client from db_service (reuse existing setup)
from db_service import supabase

if supabase is None:
    print("❌ Error: Supabase client not initialized. Check SUPABASE_URL and SUPABASE_KEY environment variables.")
    sys.exit(1)


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
        
        # Count completed projects (have canvas_data)
        completed = supabase.table("projects").select("id", count="exact")\
            .gte("created_at", date.isoformat())\
            .lt("created_at", next_date.isoformat())\
            .not_.is_("canvas_data", "null").execute()
        
        # Count exports from activity_logs (if table exists)
        try:
            exports = supabase.table("activity_logs").select("action")\
                .in_("action", ["export_pdf", "export_zip"])\
                .gte("created_at", date.isoformat())\
                .lt("created_at", next_date.isoformat()).execute()
        except Exception:
            exports = type('obj', (object,), {'data': []})()  # Empty result
        
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


def aggregate_generation_stats():
    """
    Aggregate AI generation statistics
    AI 生成统计聚合
    """
    log("🎨 Starting generation stats aggregation...")
    
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=30)).isoformat()
    
    # Get generation events from user_events
    events = supabase.table("user_events").select("event_type, properties")\
        .in_("event_type", ["generation_start", "generation_complete", "generation_failed"])\
        .gte("created_at", start_date).execute()
    
    stats = {
        "total_generations": 0,
        "successful": 0,
        "failed": 0,
        "success_rate": 0,
    }
    
    for event in events.data or []:
        event_type = event.get("event_type")
        if event_type == "generation_start":
            stats["total_generations"] += 1
        elif event_type == "generation_complete":
            stats["successful"] += 1
        elif event_type == "generation_failed":
            stats["failed"] += 1
    
    if stats["total_generations"] > 0:
        stats["success_rate"] = round(stats["successful"] / stats["total_generations"] * 100, 1)
    
    # Also get from credit_transactions as backup
    credits_used = supabase.table("credit_transactions").select("id", count="exact")\
        .eq("type", "generation")\
        .gte("created_at", start_date).execute()
    stats["credits_transactions"] = credits_used.count or 0
    
    stats_data = {
        "date": now.strftime("%Y-%m-%d"),
        "stat_type": "generation_stats_30d",
        "data": stats,
        "updated_at": now.isoformat()
    }
    
    supabase.table("aggregated_stats").upsert(
        stats_data,
        on_conflict="date,stat_type"
    ).execute()
    
    log("✅ Generation stats aggregation complete")


def aggregate_marketplace_stats():
    """
    Aggregate marketplace statistics
    市场统计聚合
    """
    log("🏪 Starting marketplace stats aggregation...")
    
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=30)).isoformat()
    
    # Total listings
    total_listings = supabase.table("marketplace_listings").select("id", count="exact")\
        .eq("moderation_status", "approved").execute()
    
    # New listings this month
    new_listings = supabase.table("marketplace_listings").select("id", count="exact")\
        .eq("moderation_status", "approved")\
        .gte("created_at", start_date).execute()
    
    # Get purchases from user_purchases
    try:
        purchases = supabase.table("user_purchases").select("id, credits_paid")\
            .gte("created_at", start_date).execute()
        total_purchases = len(purchases.data or [])
        total_revenue = sum(p.get("credits_paid", 0) for p in purchases.data or [])
    except Exception:
        total_purchases = 0
        total_revenue = 0
    
    # Get usage stats from listing_usage
    try:
        usage = supabase.table("listing_usage").select("id", count="exact")\
            .gte("used_at", start_date).execute()
        total_usage = usage.count or 0
    except Exception:
        total_usage = 0
    
    stats_data = {
        "date": now.strftime("%Y-%m-%d"),
        "stat_type": "marketplace_stats_30d",
        "data": {
            "total_listings": total_listings.count or 0,
            "new_listings": new_listings.count or 0,
            "total_purchases": total_purchases,
            "total_revenue_credits": total_revenue,
            "total_usage": total_usage,
        },
        "updated_at": now.isoformat()
    }
    
    supabase.table("aggregated_stats").upsert(
        stats_data,
        on_conflict="date,stat_type"
    ).execute()
    
    log("✅ Marketplace stats aggregation complete")


def aggregate_retention_stats():
    """
    Aggregate user retention statistics
    用户留存统计聚合
    """
    log("📈 Starting retention stats aggregation...")
    
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    retention_data = {}
    
    for period_name, days in [("D1", 1), ("D7", 7), ("D30", 30)]:
        # Users who signed up X days ago
        signup_date = today - timedelta(days=days)
        next_day = signup_date + timedelta(days=1)
        
        cohort = supabase.table("profiles").select("id")\
            .gte("created_at", signup_date.isoformat())\
            .lt("created_at", next_day.isoformat()).execute()
        
        cohort_ids = [u.get("id") for u in cohort.data or []]
        cohort_size = len(cohort_ids)
        
        if cohort_size == 0:
            retention_data[period_name] = {"cohort_size": 0, "retained": 0, "rate": 0}
            continue
        
        # Check how many were active today
        active_today = supabase.table("activity_logs").select("user_id")\
            .in_("user_id", cohort_ids[:100])  # Limit to avoid query issues
            .gte("created_at", today.isoformat())\
            .lt("created_at", now.isoformat()).execute()
        
        retained = len(set(a.get("user_id") for a in active_today.data or []))
        
        retention_data[period_name] = {
            "cohort_size": cohort_size,
            "retained": retained,
            "rate": round(retained / min(cohort_size, 100) * 100, 1) if cohort_size > 0 else 0
        }
    
    stats_data = {
        "date": now.strftime("%Y-%m-%d"),
        "stat_type": "retention_stats",
        "data": retention_data,
        "updated_at": now.isoformat()
    }
    
    supabase.table("aggregated_stats").upsert(
        stats_data,
        on_conflict="date,stat_type"
    ).execute()
    
    log("✅ Retention stats aggregation complete")


def aggregate_feature_usage():
    """
    Aggregate feature usage statistics
    功能使用统计聚合
    """
    log("⚙️ Starting feature usage aggregation...")
    
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=7)).isoformat()
    
    # Get button clicks and feature events
    events = supabase.table("user_events").select("event_type, properties")\
        .in_("event_type", ["button_click", "feature_discovery", "modal_open"])\
        .gte("created_at", start_date).execute()
    
    feature_counts = defaultdict(int)
    button_counts = defaultdict(int)
    
    for event in events.data or []:
        event_type = event.get("event_type")
        props = event.get("properties", {})
        
        if event_type == "button_click":
            button_name = props.get("button_name", "unknown")
            button_counts[button_name] += 1
        elif event_type == "feature_discovery":
            feature_name = props.get("feature_name", "unknown")
            feature_counts[feature_name] += 1
    
    stats_data = {
        "date": now.strftime("%Y-%m-%d"),
        "stat_type": "feature_usage_7d",
        "data": {
            "buttons": dict(sorted(button_counts.items(), key=lambda x: -x[1])[:20]),
            "features": dict(sorted(feature_counts.items(), key=lambda x: -x[1])[:20]),
        },
        "updated_at": now.isoformat()
    }
    
    supabase.table("aggregated_stats").upsert(
        stats_data,
        on_conflict="date,stat_type"
    ).execute()
    
    log("✅ Feature usage aggregation complete")


def aggregate_export_stats():
    """
    Aggregate export/download statistics
    导出/下载操作统计聚合（PDF、ZIP、打印、预览）
    """
    log("📊 Starting export stats aggregation...")
    
    now = datetime.now(timezone.utc)
    
    # 统计最近30天的导出数据
    stats_by_date = {}
    total_pdf = 0
    total_zip = 0
    total_print = 0
    total_preview = 0
    
    for i in range(30):
        date = (now - timedelta(days=i)).date()
        date_str = date.isoformat()
        next_date = date + timedelta(days=1)
        
        try:
            # 从 activity_logs 统计
            logs = supabase.table("activity_logs").select("action")\
                .in_("action", ["download_pdf", "export_zip", "print_project", "preview_pdf"])\
                .gte("created_at", date.isoformat())\
                .lt("created_at", next_date.isoformat()).execute()
            
            day_stats = {"pdf": 0, "zip": 0, "print": 0, "preview": 0}
            for log_entry in logs.data or []:
                action = log_entry.get("action", "")
                if action == "download_pdf":
                    day_stats["pdf"] += 1
                    total_pdf += 1
                elif action == "export_zip":
                    day_stats["zip"] += 1
                    total_zip += 1
                elif action == "print_project":
                    day_stats["print"] += 1
                    total_print += 1
                elif action == "preview_pdf":
                    day_stats["preview"] += 1
                    total_preview += 1
            
            stats_by_date[date_str] = day_stats
        except Exception as e:
            log(f"  Warning: Failed to get export logs for {date_str}: {e}")
    
    # 构建趋势数据（最近30天，从旧到新排序）
    trend_data = []
    for i in range(29, -1, -1):
        date = (now - timedelta(days=i)).date()
        date_str = date.isoformat()
        day_stats = stats_by_date.get(date_str, {"pdf": 0, "zip": 0, "print": 0, "preview": 0})
        trend_data.append({
            "date": date.strftime("%m/%d"),
            **day_stats
        })
    
    stats_data = {
        "date": now.strftime("%Y-%m-%d"),
        "stat_type": "export_stats_30d",
        "data": {
            "totalPdf": total_pdf,
            "totalZip": total_zip,
            "totalPrint": total_print,
            "totalPreview": total_preview,
            "trend": trend_data
        },
        "updated_at": now.isoformat()
    }
    
    supabase.table("aggregated_stats").upsert(
        stats_data,
        on_conflict="date,stat_type"
    ).execute()
    
    log(f"✅ Export stats aggregation complete: PDF={total_pdf}, ZIP={total_zip}, Print={total_print}, Preview={total_preview}")


def run_hourly_tasks():
    """Run tasks that should be executed hourly"""
    log("🕐 Running hourly aggregation tasks...")
    
    aggregate_tier_distribution()
    aggregate_event_stats()
    aggregate_feature_usage()
    
    log("✅ Hourly tasks complete")


def run_daily_tasks():
    """Run tasks that should be executed daily"""
    log("📅 Running daily aggregation tasks...")
    
    aggregate_daily_user_stats()
    aggregate_daily_revenue()
    aggregate_daily_projects()
    aggregate_credit_usage()
    aggregate_conversion_funnel()
    aggregate_generation_stats()
    aggregate_marketplace_stats()
    aggregate_retention_stats()
    aggregate_export_stats()
    
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

