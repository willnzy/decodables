#!/usr/bin/env python3
"""
Campaign & Holiday Theme Scheduler (v3.14)

Scheduled task to automatically manage campaign lifecycle and holiday themes.

Features:
1. Auto-activate scheduled campaigns when start_at is reached
2. Auto-end campaigns when end_at is passed
3. Send campaign notifications (optional)
4. Log theme transitions for analytics

Usage:
    python scheduled_tasks/campaign_scheduler.py              # Run full check
    python scheduled_tasks/campaign_scheduler.py --campaigns  # Campaigns only
    python scheduled_tasks/campaign_scheduler.py --themes     # Themes only

Cron example (run every 5 minutes):
    */5 * * * * cd /path/to/decodables && python scheduled_tasks/campaign_scheduler.py

Cron example (run every hour):
    0 * * * * cd /path/to/decodables && python scheduled_tasks/campaign_scheduler.py
"""

import os
import sys
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from services.db_service import supabase

if supabase is None:
    print("❌ Error: Supabase client not initialized")
    sys.exit(1)

# Import from submodules
from campaign_scheduler import (
    calculate_dynamic_date,
    is_theme_active,
    update_campaign_statuses,
    get_upcoming_campaigns,
    log_current_theme,
    get_upcoming_themes,
    generate_summary_report,
    log,
)


def run_scheduler(campaigns: bool = True, themes: bool = True, use_logger: bool = True):
    """Run the scheduler tasks."""
    
    # Determine task type for logging
    if campaigns and themes:
        task_type = 'full'
    elif campaigns:
        task_type = 'campaigns'
    else:
        task_type = 'themes'
    
    # Import TaskLogger
    task_logger = None
    if use_logger:
        try:
            from task_logger import TaskLogger
            task_logger = TaskLogger('campaign_scheduler', task_type)
        except ImportError:
            pass
    
    # Use context manager if available
    if task_logger:
        task_logger.__enter__()
    
    try:
        log("=" * 60)
        log("🚀 Campaign & Theme Scheduler Started")
        log("=" * 60)
        
        campaign_results = {"activated": 0, "ended": 0, "errors": 0}
        current_theme = None
        
        if campaigns:
            log("\n📢 Processing Campaigns...")
            campaign_results = update_campaign_statuses()
            log(f"   Activated: {campaign_results['activated']}, Ended: {campaign_results['ended']}, Errors: {campaign_results['errors']}")
            
            # Check upcoming campaigns
            upcoming = get_upcoming_campaigns(24)
            if upcoming:
                log(f"\n⏰ {len(upcoming)} campaign(s) starting in next 24 hours:")
                for c in upcoming:
                    log(f"   - {c['name']} (starts at {c['start_at']})")
        
        if themes:
            log("\n🎨 Checking Holiday Themes...")
            current_theme_data = log_current_theme()
            current_theme = current_theme_data['name'] if current_theme_data else None
            
            # Check upcoming themes
            upcoming = get_upcoming_themes(7)
            if upcoming:
                log(f"\n📅 {len(upcoming)} theme(s) coming in next 7 days:")
                for t in upcoming:
                    log(f"   - {t['name']} (in {t['starts_in_days']} days)")
        
        # Generate summary
        log("\n📊 Summary Report:")
        report = generate_summary_report()
        log(f"   Campaigns: {report['campaigns']['active']} active, {report['campaigns']['scheduled']} scheduled")
        log(f"   Themes: {report['themes']['total']} configured, Current: {report['themes']['current'] or 'None'}")
        
        log("\n" + "=" * 60)
        log("✅ Scheduler completed successfully")
        log("=" * 60)
        
        # Set task result for logging
        if task_logger:
            task_logger.set_result({
                'campaigns_activated': campaign_results['activated'],
                'campaigns_ended': campaign_results['ended'],
                'campaigns_errors': campaign_results['errors'],
                'campaigns_active': report['campaigns']['active'],
                'campaigns_scheduled': report['campaigns']['scheduled'],
                'current_theme': current_theme,
                'themes_total': report['themes']['total'],
            })
        
        return report
        
    except Exception as e:
        log(f"❌ Scheduler failed: {e}", "ERROR")
        raise
    
    finally:
        if task_logger:
            task_logger.__exit__(None, None, None)


# Backward compatibility exports
__all__ = [
    'calculate_dynamic_date',
    'is_theme_active',
    'update_campaign_statuses',
    'get_upcoming_campaigns',
    'log_current_theme',
    'get_upcoming_themes',
    'generate_summary_report',
    'run_scheduler',
    'log',
]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Campaign & Theme Scheduler')
    parser.add_argument('--campaigns', action='store_true', help='Process campaigns only')
    parser.add_argument('--themes', action='store_true', help='Process themes only')
    parser.add_argument('--report', action='store_true', help='Generate report only')
    parser.add_argument('--no-log', action='store_true', help='Disable task logging to database')
    
    args = parser.parse_args()
    
    if args.report:
        report = generate_summary_report()
        import json
        print(json.dumps(report, indent=2))
    else:
        # Default: run both if neither specified
        campaigns = args.campaigns or not args.themes
        themes = args.themes or not args.campaigns
        run_scheduler(campaigns=campaigns, themes=themes, use_logger=not args.no_log)
