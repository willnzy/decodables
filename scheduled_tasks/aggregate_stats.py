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


def aggregate_tier_activity():
    """
    Aggregate user activity by tier
    按用户等级统计活跃度
    """
    log("👥 Starting tier activity aggregation...")
    
    now = datetime.now(timezone.utc)
    
    # 统计各等级的活跃情况（最近7天）
    tier_activity = {}
    tiers = ["free", "starter", "pro"]
    
    for tier in tiers:
        # 获取该等级的所有用户
        users = supabase.table("profiles").select("id")\
            .eq("tier", tier).execute()
        user_ids = [u.get("id") for u in users.data or []]
        total_users = len(user_ids)
        
        if total_users == 0:
            tier_activity[tier] = {
                "total_users": 0,
                "active_7d": 0,
                "active_rate": 0,
                "avg_actions_per_user": 0
            }
            continue
        
        # 统计活跃用户（最近7天有活动）
        start_date = (now - timedelta(days=7)).isoformat()
        
        active_users_set = set()
        total_actions = 0
        
        # 分批查询（避免查询太大）
        batch_size = 100
        for i in range(0, min(len(user_ids), 500), batch_size):
            batch_ids = user_ids[i:i+batch_size]
            logs = supabase.table("activity_logs").select("user_id")\
                .in_("user_id", batch_ids)\
                .gte("created_at", start_date).execute()
            for log_entry in logs.data or []:
                active_users_set.add(log_entry.get("user_id"))
                total_actions += 1
        
        active_count = len(active_users_set)
        tier_activity[tier] = {
            "total_users": total_users,
            "active_7d": active_count,
            "active_rate": round(active_count / total_users * 100, 1) if total_users > 0 else 0,
            "avg_actions_per_user": round(total_actions / active_count, 1) if active_count > 0 else 0
        }
    
    stats_data = {
        "date": now.strftime("%Y-%m-%d"),
        "stat_type": "tier_activity",
        "data": tier_activity,
        "updated_at": now.isoformat()
    }
    
    supabase.table("aggregated_stats").upsert(
        stats_data,
        on_conflict="date,stat_type"
    ).execute()
    
    log("✅ Tier activity aggregation complete")


def aggregate_subscription_events():
    """
    Aggregate subscription events (upgrades, downgrades, cancellations, refunds)
    订阅事件统计（升级、降级、取消、退款）
    """
    log("💳 Starting subscription events aggregation...")
    
    now = datetime.now(timezone.utc)
    
    # 最近30天的事件统计
    subscription_stats_by_date = {}
    total_upgrades = 0
    total_downgrades = 0
    total_cancellations = 0
    total_refunds = 0
    
    for i in range(30):
        date = (now - timedelta(days=i)).date()
        date_str = date.isoformat()
        next_date = date + timedelta(days=1)
        
        day_stats = {"upgrades": 0, "downgrades": 0, "cancellations": 0, "refunds": 0}
        
        # 从 admin_operation_logs 获取管理员操作记录
        try:
            logs = supabase.table("admin_operation_logs").select("action")\
                .in_("action", ["tier_upgraded", "tier_downgraded", "subscription_cancelled", "refund_processed"])\
                .gte("created_at", date.isoformat())\
                .lt("created_at", next_date.isoformat()).execute()
            
            for log_entry in logs.data or []:
                action = log_entry.get("action", "")
                if "upgrade" in action:
                    day_stats["upgrades"] += 1
                    total_upgrades += 1
                elif "downgrade" in action:
                    day_stats["downgrades"] += 1
                    total_downgrades += 1
                elif "cancel" in action:
                    day_stats["cancellations"] += 1
                    total_cancellations += 1
                elif "refund" in action:
                    day_stats["refunds"] += 1
                    total_refunds += 1
        except Exception as e:
            log(f"  Warning: Failed to get subscription events for {date_str}: {e}")
        
        # 也从 credit_transactions 获取退款记录
        try:
            refunds = supabase.table("credit_transactions").select("id", count="exact")\
                .eq("type", "refund")\
                .gte("created_at", date.isoformat())\
                .lt("created_at", next_date.isoformat()).execute()
            day_stats["refunds"] += refunds.count or 0
            total_refunds += refunds.count or 0
        except Exception:
            pass
        
        subscription_stats_by_date[date_str] = day_stats
    
    # 构建趋势数据
    trend_data = []
    for i in range(29, -1, -1):
        date = (now - timedelta(days=i)).date()
        date_str = date.isoformat()
        day_stats = subscription_stats_by_date.get(date_str, {"upgrades": 0, "downgrades": 0, "cancellations": 0, "refunds": 0})
        trend_data.append({
            "date": date.strftime("%m/%d"),
            **day_stats
        })
    
    stats_data = {
        "date": now.strftime("%Y-%m-%d"),
        "stat_type": "subscription_events_30d",
        "data": {
            "totalUpgrades": total_upgrades,
            "totalDowngrades": total_downgrades,
            "totalCancellations": total_cancellations,
            "totalRefunds": total_refunds,
            "trend": trend_data
        },
        "updated_at": now.isoformat()
    }
    
    supabase.table("aggregated_stats").upsert(
        stats_data,
        on_conflict="date,stat_type"
    ).execute()
    
    log(f"✅ Subscription events aggregation complete: Up={total_upgrades}, Down={total_downgrades}, Cancel={total_cancellations}, Refund={total_refunds}")


def aggregate_page_views():
    """
    Aggregate page view statistics
    页面访问统计聚合
    """
    log("📄 Starting page view aggregation...")
    
    now = datetime.now(timezone.utc)
    
    # 从 user_events 获取页面访问数据
    start_date = (now - timedelta(days=7)).isoformat()
    
    try:
        events = supabase.table("user_events").select("properties")\
            .eq("event_type", "page_view")\
            .gte("created_at", start_date).execute()
        
        page_counts = defaultdict(int)
        page_tier_counts = defaultdict(lambda: defaultdict(int))
        
        for event in events.data or []:
            props = event.get("properties", {})
            page_name = props.get("page_name", "unknown")
            user_tier = props.get("user_tier", "guest")
            
            page_counts[page_name] += 1
            page_tier_counts[page_name][user_tier] += 1
        
        # 转换为可存储格式
        page_data = {}
        for page, count in page_counts.items():
            page_data[page] = {
                "total": count,
                "by_tier": dict(page_tier_counts[page])
            }
        
        stats_data = {
            "date": now.strftime("%Y-%m-%d"),
            "stat_type": "page_views_7d",
            "data": {
                "pages": page_data,
                "total_views": sum(page_counts.values()),
                "guest_views": sum(1 for e in events.data or [] if e.get("properties", {}).get("user_tier") == "guest")
            },
            "updated_at": now.isoformat()
        }
        
        supabase.table("aggregated_stats").upsert(
            stats_data,
            on_conflict="date,stat_type"
        ).execute()
        
        log(f"✅ Page view aggregation complete: {sum(page_counts.values())} total views")
    except Exception as e:
        log(f"❌ Page view aggregation failed: {e}")


def aggregate_project_details():
    """
    Aggregate detailed project statistics (deletions, OCR usage, page counts)
    项目详细统计（删除、OCR使用、页面数）
    """
    log("📁 Starting project details aggregation...")
    
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=30)).isoformat()
    
    # 统计删除的项目
    deleted_count = supabase.table("projects").select("id", count="exact")\
        .eq("is_deleted", True)\
        .gte("deleted_at", start_date).execute()
    
    # 统计 OCR 使用（从 user_events）
    try:
        ocr_events = supabase.table("user_events").select("id", count="exact")\
            .eq("event_type", "ocr_scan")\
            .gte("created_at", start_date).execute()
        ocr_count = ocr_events.count or 0
    except Exception:
        ocr_count = 0
    
    # 统计页面总数（从 projects.canvas_data）
    # 注：这需要解析 JSONB，比较复杂，用估算
    projects_with_data = supabase.table("projects").select("canvas_data")\
        .not_.is_("canvas_data", "null")\
        .gte("created_at", start_date)\
        .limit(500).execute()
    
    total_pages = 0
    for proj in projects_with_data.data or []:
        canvas_data = proj.get("canvas_data", {})
        if isinstance(canvas_data, dict):
            pages = canvas_data.get("pages", [])
            total_pages += len(pages) if isinstance(pages, list) else 0
    
    avg_pages_per_project = round(total_pages / len(projects_with_data.data), 1) if projects_with_data.data else 0
    
    stats_data = {
        "date": now.strftime("%Y-%m-%d"),
        "stat_type": "project_details_30d",
        "data": {
            "deleted_projects": deleted_count.count or 0,
            "ocr_usage": ocr_count,
            "total_pages_sample": total_pages,
            "avg_pages_per_project": avg_pages_per_project
        },
        "updated_at": now.isoformat()
    }
    
    supabase.table("aggregated_stats").upsert(
        stats_data,
        on_conflict="date,stat_type"
    ).execute()
    
    log(f"✅ Project details aggregation complete: deleted={deleted_count.count or 0}, OCR={ocr_count}")


def aggregate_returning_users():
    """
    Aggregate returning user statistics (users who came back after inactivity)
    回流用户统计（不活跃后回归的用户）
    """
    log("🔄 Starting returning users aggregation...")
    
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    returning_data = {}
    
    for period_days in [7, 14, 30]:
        # 用户在 X 天前不活跃，但今天又活跃了
        inactive_start = today - timedelta(days=period_days)
        inactive_end = today - timedelta(days=1)
        
        # 获取今天活跃的用户
        active_today = supabase.table("activity_logs").select("user_id")\
            .gte("created_at", today.isoformat())\
            .lt("created_at", now.isoformat()).execute()
        active_today_ids = set(a.get("user_id") for a in active_today.data or [])
        
        if not active_today_ids:
            returning_data[f"returning_{period_days}d"] = {"count": 0, "ids": []}
            continue
        
        # 检查这些用户在过去 X 天是否不活跃
        returning_users = []
        for user_id in list(active_today_ids)[:100]:  # 限制检查数量
            activity_in_period = supabase.table("activity_logs").select("id", count="exact")\
                .eq("user_id", user_id)\
                .gte("created_at", inactive_start.isoformat())\
                .lt("created_at", inactive_end.isoformat()).execute()
            
            if (activity_in_period.count or 0) == 0:
                # 确认用户在更早之前有过活动
                earlier_activity = supabase.table("activity_logs").select("id", count="exact")\
                    .eq("user_id", user_id)\
                    .lt("created_at", inactive_start.isoformat()).execute()
                
                if (earlier_activity.count or 0) > 0:
                    returning_users.append(user_id)
        
        returning_data[f"returning_{period_days}d"] = {
            "count": len(returning_users),
            "sample_ids": returning_users[:10]  # 只保存前10个作为示例
        }
    
    stats_data = {
        "date": now.strftime("%Y-%m-%d"),
        "stat_type": "returning_users",
        "data": returning_data,
        "updated_at": now.isoformat()
    }
    
    supabase.table("aggregated_stats").upsert(
        stats_data,
        on_conflict="date,stat_type"
    ).execute()
    
    log(f"✅ Returning users aggregation complete")


def aggregate_tier_trend():
    """
    Aggregate tier distribution trend over time
    各等级用户数趋势聚合
    """
    log("📈 Starting tier trend aggregation...")
    
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    trend_data = []
    
    for i in range(30):
        date = today - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        next_date = date + timedelta(days=1)
        
        # 统计截止到该日期的各等级用户数
        # 注：这是一个简化的统计，实际应该用快照或更精确的方法
        tier_counts = {}
        for tier in ["free", "starter", "pro"]:
            count = supabase.table("profiles").select("id", count="exact")\
                .eq("tier", tier)\
                .lt("created_at", next_date.isoformat()).execute()
            tier_counts[tier] = count.count or 0
        
        # 估算游客数（注册用户的4倍减去已注册）
        total_registered = sum(tier_counts.values())
        tier_counts["guest"] = total_registered * 3  # 估算
        
        trend_data.append({
            "date": date.strftime("%m/%d"),
            **tier_counts
        })
    
    # 反转使其从旧到新
    trend_data.reverse()
    
    stats_data = {
        "date": now.strftime("%Y-%m-%d"),
        "stat_type": "tier_trend_30d",
        "data": {"trend": trend_data},
        "updated_at": now.isoformat()
    }
    
    supabase.table("aggregated_stats").upsert(
        stats_data,
        on_conflict="date,stat_type"
    ).execute()
    
    log("✅ Tier trend aggregation complete")


def aggregate_tier_conversion():
    """
    Aggregate tier conversion data (guest->free, free->starter, etc.)
    用户转化数据聚合
    """
    log("🔄 Starting tier conversion aggregation...")
    
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=30)).isoformat()
    
    conversion_data = []
    
    # 从 admin_operation_logs 获取等级变更记录
    try:
        logs = supabase.table("admin_operation_logs").select("action, details")\
            .in_("action", ["tier_upgraded", "tier_changed", "tier_downgraded"])\
            .gte("created_at", start_date).execute()
        
        conversion_counts = defaultdict(lambda: {"count": 0})
        
        for log_entry in logs.data or []:
            details = log_entry.get("details", {})
            old_tier = details.get("old_tier", "").lower()
            new_tier = details.get("new_tier", "").lower()
            
            if old_tier and new_tier and old_tier != new_tier:
                key = f"{old_tier}_{new_tier}"
                conversion_counts[key]["count"] += 1
        
        # 转换为列表格式
        for key, data in conversion_counts.items():
            parts = key.split("_")
            if len(parts) == 2:
                conversion_data.append({
                    "from": parts[0].capitalize() if parts[0] != "free" else "Free",
                    "to": parts[1].capitalize() if parts[1] != "free" else "Free",
                    "count": data["count"],
                    "rate": 0  # 需要更多数据来计算转化率
                })
    except Exception as e:
        log(f"  Warning: Failed to get conversion logs: {e}")
    
    # 添加游客到 Free 的转化（新注册用户）
    new_free = supabase.table("profiles").select("id", count="exact")\
        .eq("tier", "free")\
        .gte("created_at", start_date).execute()
    
    conversion_data.append({
        "from": "Guest",
        "to": "Free",
        "count": new_free.count or 0,
        "rate": 25  # 估算值，可基于 session 数据计算
    })
    
    # 添加游客直接到付费的转化
    new_paid = supabase.table("profiles").select("id", count="exact")\
        .in_("tier", ["starter", "pro"])\
        .gte("created_at", start_date).execute()
    
    if (new_paid.count or 0) > 0:
        conversion_data.append({
            "from": "Guest",
            "to": "Starter/Pro",
            "count": new_paid.count or 0,
            "rate": 5  # 估算值
        })
    
    stats_data = {
        "date": now.strftime("%Y-%m-%d"),
        "stat_type": "tier_conversion_30d",
        "data": {"conversions": conversion_data},
        "updated_at": now.isoformat()
    }
    
    supabase.table("aggregated_stats").upsert(
        stats_data,
        on_conflict="date,stat_type"
    ).execute()
    
    log(f"✅ Tier conversion aggregation complete: {len(conversion_data)} conversion paths")


def aggregate_asset_usage():
    """
    Aggregate marketplace asset usage statistics
    素材使用排名统计聚合
    """
    log("🎨 Starting asset usage aggregation...")
    
    now = datetime.now(timezone.utc)
    
    # 获取所有使用记录并关联 listing 信息
    try:
        # 获取 listing_usage 并关联 marketplace_listings
        usage_data = supabase.table("listing_usage").select(
            "listing_id, used_by_user_id, used_at, marketplace_listings(id, title, thumbnail_url, resource_type, seller_id)"
        ).execute()
        
        # 统计每个素材的使用次数
        usage_counts = defaultdict(lambda: {"count": 0, "unique_users": set(), "listing": None})
        
        for record in usage_data.data or []:
            listing_id = record.get("listing_id")
            user_id = record.get("used_by_user_id")
            listing_info = record.get("marketplace_listings", {})
            
            if listing_id:
                usage_counts[listing_id]["count"] += 1
                usage_counts[listing_id]["unique_users"].add(user_id)
                if not usage_counts[listing_id]["listing"]:
                    usage_counts[listing_id]["listing"] = listing_info
        
        # 转换为排名列表
        rankings = []
        for listing_id, data in usage_counts.items():
            listing = data["listing"] or {}
            rankings.append({
                "listing_id": listing_id,
                "title": listing.get("title", "Unknown"),
                "thumbnail_url": listing.get("thumbnail_url", ""),
                "resource_type": listing.get("resource_type", ""),
                "seller_id": listing.get("seller_id", ""),
                "usage_count": data["count"],
                "unique_users": len(data["unique_users"])
            })
        
        # 按使用次数排序，取前50
        rankings.sort(key=lambda x: -x["usage_count"])
        top_assets = rankings[:50]
        
        # 按类型分组排名
        by_type = {}
        for item in rankings:
            rtype = item.get("resource_type", "other")
            if rtype not in by_type:
                by_type[rtype] = []
            if len(by_type[rtype]) < 20:  # 每类型取前20
                by_type[rtype].append(item)
        
        stats_data = {
            "date": now.strftime("%Y-%m-%d"),
            "stat_type": "asset_usage_ranking",
            "data": {
                "top_assets": top_assets,
                "by_type": by_type,
                "total_usage": sum(item["usage_count"] for item in rankings),
                "total_assets_used": len(rankings)
            },
            "updated_at": now.isoformat()
        }
        
        supabase.table("aggregated_stats").upsert(
            stats_data,
            on_conflict="date,stat_type"
        ).execute()
        
        log(f"✅ Asset usage aggregation complete: {len(top_assets)} top assets, {len(rankings)} total")
    except Exception as e:
        log(f"❌ Asset usage aggregation failed: {e}")


def aggregate_performance_metrics():
    """
    Aggregate page performance metrics (Core Web Vitals)
    页面性能指标聚合
    """
    log("⚡ Starting performance metrics aggregation...")
    
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=7)).isoformat()
    
    try:
        # 从 user_events 获取性能指标事件
        events = supabase.table("user_events").select("properties")\
            .eq("event_type", "performance_metrics")\
            .gte("created_at", start_date).execute()
        
        if not events.data:
            log("  No performance data found")
            return
        
        # 聚合各项指标
        metrics_agg = {
            "lcp": {"values": [], "ratings": defaultdict(int)},
            "fid": {"values": [], "ratings": defaultdict(int)},
            "cls": {"values": [], "ratings": defaultdict(int)},
            "fcp": {"values": [], "ratings": defaultdict(int)},
            "ttfb": {"values": [], "ratings": defaultdict(int)},
            "dom_complete": {"values": []},
            "load_complete": {"values": []},
        }
        
        page_metrics = defaultdict(lambda: {"count": 0, "lcp_sum": 0, "fcp_sum": 0})
        
        for event in events.data or []:
            props = event.get("properties", {})
            page_url = props.get("page_url", "/")
            
            # 聚合各项指标
            for metric in ["lcp", "fid", "cls", "fcp", "ttfb", "domComplete", "loadComplete"]:
                key = metric.lower().replace("complete", "_complete")
                value = props.get(metric) or props.get(key)
                if value is not None and isinstance(value, (int, float)):
                    if key in metrics_agg:
                        metrics_agg[key]["values"].append(value)
                    
                    # 统计评级
                    rating = props.get(f"{metric}_rating") or props.get(f"{key}_rating")
                    if rating and key in metrics_agg and "ratings" in metrics_agg[key]:
                        metrics_agg[key]["ratings"][rating] += 1
            
            # 按页面聚合
            page_metrics[page_url]["count"] += 1
            if lcp := props.get("lcp"):
                page_metrics[page_url]["lcp_sum"] += lcp
            if fcp := props.get("fcp"):
                page_metrics[page_url]["fcp_sum"] += fcp
        
        # 计算统计值
        def calc_stats(values):
            if not values:
                return {"avg": 0, "p50": 0, "p75": 0, "p95": 0, "count": 0}
            sorted_vals = sorted(values)
            n = len(sorted_vals)
            return {
                "avg": round(sum(values) / n, 1),
                "p50": sorted_vals[int(n * 0.5)] if n > 0 else 0,
                "p75": sorted_vals[int(n * 0.75)] if n > 0 else 0,
                "p95": sorted_vals[int(n * 0.95)] if n > 0 else 0,
                "count": n
            }
        
        # 构建聚合数据
        aggregated = {}
        for key, data in metrics_agg.items():
            aggregated[key] = {
                "stats": calc_stats(data["values"]),
                "ratings": dict(data.get("ratings", {}))
            }
        
        # 按页面的平均指标
        page_averages = {}
        for page, data in page_metrics.items():
            if data["count"] > 0:
                page_averages[page] = {
                    "count": data["count"],
                    "avg_lcp": round(data["lcp_sum"] / data["count"], 1) if data["lcp_sum"] else 0,
                    "avg_fcp": round(data["fcp_sum"] / data["count"], 1) if data["fcp_sum"] else 0,
                }
        
        stats_data = {
            "date": now.strftime("%Y-%m-%d"),
            "stat_type": "performance_metrics_7d",
            "data": {
                "metrics": aggregated,
                "by_page": dict(sorted(page_averages.items(), key=lambda x: -x[1]["count"])[:20]),
                "total_samples": len(events.data),
            },
            "updated_at": now.isoformat()
        }
        
        supabase.table("aggregated_stats").upsert(
            stats_data,
            on_conflict="date,stat_type"
        ).execute()
        
        log(f"✅ Performance metrics aggregation complete: {len(events.data)} samples")
    except Exception as e:
        log(f"❌ Performance metrics aggregation failed: {e}")


def aggregate_user_distribution():
    """
    Aggregate user distribution by country, browser, OS, device
    用户地理/设备分布聚合
    """
    log("🌍 Starting user distribution aggregation...")
    
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=7)).isoformat()
    
    try:
        # 从 user_events 获取 session_start 事件
        events = supabase.table("user_events").select("properties")\
            .eq("event_type", "session_start")\
            .gte("created_at", start_date).execute()
        
        if not events.data:
            log("  No session data found")
            return
        
        # 聚合分布数据
        distributions = {
            "country": defaultdict(int),
            "browser": defaultdict(int),
            "os": defaultdict(int),
            "device_type": defaultdict(int),
            "language": defaultdict(int),
            "timezone": defaultdict(int),
        }
        
        for event in events.data or []:
            props = event.get("properties", {})
            
            # 国家（优先使用服务端数据）
            country = props.get("server_country") or props.get("country_code") or "unknown"
            distributions["country"][country] += 1
            
            # 浏览器
            browser = props.get("client_browser") or props.get("browser") or "unknown"
            # 简化浏览器名称
            browser_name = browser.split()[0] if browser else "unknown"
            distributions["browser"][browser_name] += 1
            
            # 操作系统
            os_info = props.get("client_os") or props.get("os") or "unknown"
            # 简化 OS 名称
            os_name = os_info.split()[0] if os_info else "unknown"
            distributions["os"][os_name] += 1
            
            # 设备类型
            device = props.get("client_device_type") or props.get("device_type") or "unknown"
            distributions["device_type"][device] += 1
            
            # 语言
            lang = props.get("client_language") or props.get("language") or "unknown"
            # 简化语言代码
            lang_code = lang.split("-")[0] if lang else "unknown"
            distributions["language"][lang_code] += 1
            
            # 时区
            tz = props.get("client_timezone") or props.get("timezone") or "unknown"
            distributions["timezone"][tz] += 1
        
        # 转换为列表格式并排序
        result = {}
        for key, counts in distributions.items():
            sorted_items = sorted(counts.items(), key=lambda x: -x[1])[:30]  # Top 30
            result[key] = [{"name": k, "count": v} for k, v in sorted_items]
        
        stats_data = {
            "date": now.strftime("%Y-%m-%d"),
            "stat_type": "user_distribution_7d",
            "data": {
                **result,
                "total_sessions": len(events.data),
            },
            "updated_at": now.isoformat()
        }
        
        supabase.table("aggregated_stats").upsert(
            stats_data,
            on_conflict="date,stat_type"
        ).execute()
        
        log(f"✅ User distribution aggregation complete: {len(events.data)} sessions")
    except Exception as e:
        log(f"❌ User distribution aggregation failed: {e}")


def run_hourly_tasks():
    """Run tasks that should be executed hourly"""
    log("🕐 Running hourly aggregation tasks...")
    
    aggregate_tier_distribution()
    aggregate_event_stats()
    aggregate_feature_usage()
    aggregate_page_views()
    aggregate_performance_metrics()  # 新增：性能指标聚合
    aggregate_user_distribution()    # 新增：用户分布聚合
    
    log("✅ Hourly tasks complete")


def cleanup_expired_deleted_projects():
    """
    清理30天前删除的项目（永久删除）
    Projects deleted more than 30 days ago are permanently removed
    """
    log("🗑️ Cleaning up expired deleted projects...")
    
    try:
        # 计算30天前的时间
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        
        # 查找需要永久删除的项目
        expired_projects = supabase.table("projects").select("id, title, user_id, deleted_at")\
            .eq("is_deleted", True)\
            .lt("deleted_at", cutoff_date)\
            .execute()
        
        if not expired_projects.data:
            log("   No expired deleted projects to clean up")
            return
        
        count = len(expired_projects.data)
        log(f"   Found {count} projects to permanently delete")
        
        # 永久删除这些项目
        for project in expired_projects.data:
            try:
                supabase.table("projects").delete().eq("id", project["id"]).execute()
                log(f"   Deleted: {project['id']} ({project.get('title', 'Untitled')})")
            except Exception as e:
                log(f"   ❌ Failed to delete {project['id']}: {e}")
        
        log(f"   ✅ Cleaned up {count} expired deleted projects")
        
    except Exception as e:
        log(f"   ❌ Error cleaning up deleted projects: {e}")


def run_daily_tasks():
    """Run tasks that should be executed daily"""
    log("📅 Running daily aggregation tasks...")
    
    # 清理过期的已删除项目
    cleanup_expired_deleted_projects()
    
    aggregate_daily_user_stats()
    aggregate_daily_revenue()
    aggregate_daily_projects()
    aggregate_credit_usage()
    aggregate_conversion_funnel()
    aggregate_generation_stats()
    aggregate_marketplace_stats()
    aggregate_retention_stats()
    aggregate_export_stats()
    aggregate_asset_usage()
    
    # 新增聚合任务
    aggregate_tier_activity()
    aggregate_subscription_events()
    aggregate_project_details()
    aggregate_returning_users()
    aggregate_tier_trend()
    aggregate_tier_conversion()
    
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

