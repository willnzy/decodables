#!/usr/bin/env python3
"""
Metrics ETL Service Entry Point

Industry-standard SaaS metrics calculation and aggregation.

Usage:
    python scheduled_tasks/metrics_etl.py --daily    # Run daily aggregation
    python scheduled_tasks/metrics_etl.py --hourly   # Run hourly quick stats
    python scheduled_tasks/metrics_etl.py --backfill 30  # Backfill last 30 days

@module scheduled_tasks.metrics_etl
@version 3.24
"""

import sys
import argparse

from metrics_etl import (
    log, run_daily_etl, run_hourly_etl, backfill_metrics
)
from metrics_etl.utils import get_supabase


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Metrics ETL Service")
    parser.add_argument("--daily", action="store_true", help="Run daily ETL")
    parser.add_argument("--hourly", action="store_true", help="Run hourly ETL")
    parser.add_argument("--backfill", type=int, metavar="DAYS", help="Backfill N days")
    args = parser.parse_args()
    
    supabase = get_supabase()
    if not supabase:
        log("❌ Error: Supabase not initialized", "ERROR")
        sys.exit(1)
    
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
