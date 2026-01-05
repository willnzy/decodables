#!/usr/bin/env python3
"""
Scheduled Data Aggregation Task

This script runs periodic statistics aggregation tasks.

Usage:
    python scheduled_tasks/aggregate_stats.py              # Run all
    python scheduled_tasks/aggregate_stats.py --daily      # Daily only
    python scheduled_tasks/aggregate_stats.py --hourly     # Hourly only

Cron examples:
    0 * * * * cd /path/to/decodables && python scheduled_tasks/aggregate_stats.py --hourly
    0 2 * * * cd /path/to/decodables && python scheduled_tasks/aggregate_stats.py --daily

@module scheduled_tasks.aggregate_stats
@version 3.24
"""

import sys
import argparse
from datetime import datetime, timedelta, timezone

from aggregators import log, get_supabase
from aggregators.user_stats import (
    aggregate_daily_user_stats,
    aggregate_tier_distribution,
    aggregate_retention_stats,
    aggregate_returning_users,
    aggregate_tier_trend,
    aggregate_tier_conversion,
    aggregate_user_distribution,
)
from aggregators.revenue_stats import (
    aggregate_daily_revenue,
    aggregate_subscription_events,
)
from aggregators.project_stats import (
    aggregate_daily_projects,
    aggregate_project_details,
)
from aggregators.usage_stats import (
    aggregate_credit_usage,
    aggregate_generation_stats,
    aggregate_feature_usage,
    aggregate_export_stats,
    aggregate_asset_usage,
)
from aggregators.marketplace_stats import aggregate_marketplace_stats
from aggregators.analytics_stats import (
    aggregate_conversion_funnel,
    aggregate_event_stats,
    aggregate_page_views,
    aggregate_tier_activity,
    aggregate_performance_metrics,
)


def cleanup_expired_deleted_projects():
    """Clean up projects deleted more than 30 days ago."""
    log("🗑️ Starting cleanup of expired deleted projects...")
    supabase = get_supabase()
    if not supabase:
        return
    
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    
    # Get projects to permanently delete
    expired = supabase.table("projects").select("id")\
        .eq("is_deleted", True)\
        .lt("deleted_at", cutoff)\
        .limit(100).execute()
    
    if not expired.data:
        log("✅ No expired projects to clean up")
        return
    
    count = 0
    for project in expired.data:
        try:
            supabase.table("projects").update({
                "is_permanently_deleted": True
            }).eq("id", project["id"]).execute()
            count += 1
        except Exception as e:
            log(f"⚠️ Failed to clean up project {project['id']}: {e}")
    
    log(f"✅ Cleaned up {count} expired deleted projects")


def run_hourly_tasks():
    """Run hourly aggregation tasks."""
    log("⏰ Starting hourly tasks...")
    
    aggregate_tier_distribution()
    aggregate_event_stats()
    aggregate_performance_metrics()
    
    log("✅ Hourly tasks complete")


def run_daily_tasks():
    """Run daily aggregation tasks."""
    log("📅 Starting daily tasks...")
    
    # User stats
    aggregate_daily_user_stats()
    aggregate_retention_stats()
    aggregate_returning_users()
    aggregate_tier_trend()
    aggregate_tier_conversion()
    aggregate_user_distribution()
    
    # Revenue
    aggregate_daily_revenue()
    aggregate_subscription_events()
    
    # Projects & Assets
    aggregate_daily_projects()
    aggregate_project_details()
    aggregate_asset_usage()
    
    # Usage
    aggregate_credit_usage()
    aggregate_generation_stats()
    aggregate_feature_usage()
    aggregate_export_stats()
    
    # Analytics
    aggregate_conversion_funnel()
    aggregate_page_views()
    aggregate_tier_activity()
    
    # Marketplace
    aggregate_marketplace_stats()
    
    # Cleanup
    cleanup_expired_deleted_projects()
    
    log("✅ Daily tasks complete")


def run_all_tasks():
    """Run all aggregation tasks."""
    log("🚀 Starting all aggregation tasks...")
    run_hourly_tasks()
    run_daily_tasks()
    log("🎉 All tasks complete!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run aggregation tasks")
    parser.add_argument("--hourly", action="store_true", help="Run hourly tasks only")
    parser.add_argument("--daily", action="store_true", help="Run daily tasks only")
    args = parser.parse_args()
    
    supabase = get_supabase()
    if not supabase:
        log("❌ Error: Supabase not initialized")
        sys.exit(1)
    
    if args.hourly:
        run_hourly_tasks()
    elif args.daily:
        run_daily_tasks()
    else:
        run_all_tasks()


if __name__ == "__main__":
    main()
