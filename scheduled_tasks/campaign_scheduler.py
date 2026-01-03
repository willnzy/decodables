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
from datetime import datetime, timezone, date, timedelta
from typing import Optional, Dict, Any, List

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
# Theme Date Calculation (Standalone)
# ==========================================

def calculate_dynamic_date(rule: str, year: int) -> Optional[date]:
    """Calculate dynamic holiday dates."""
    if rule == 'us_thanksgiving':
        nov_first = date(year, 11, 1)
        days_until_thursday = (3 - nov_first.weekday() + 7) % 7
        first_thursday = nov_first + timedelta(days=days_until_thursday)
        return first_thursday + timedelta(weeks=3)
    
    elif rule == 'black_friday':
        thanksgiving = calculate_dynamic_date('us_thanksgiving', year)
        return thanksgiving + timedelta(days=1) if thanksgiving else None
    
    elif rule == 'mothers_day':
        may_first = date(year, 5, 1)
        days_until_sunday = (6 - may_first.weekday() + 7) % 7
        first_sunday = may_first + timedelta(days=days_until_sunday)
        if may_first.weekday() == 6:
            first_sunday = may_first
        return first_sunday + timedelta(weeks=1)
    
    elif rule == 'fathers_day':
        june_first = date(year, 6, 1)
        days_until_sunday = (6 - june_first.weekday() + 7) % 7
        first_sunday = june_first + timedelta(days=days_until_sunday)
        if june_first.weekday() == 6:
            first_sunday = june_first
        return first_sunday + timedelta(weeks=2)
    
    elif rule == 'mlk_day':
        jan_first = date(year, 1, 1)
        days_until_monday = (7 - jan_first.weekday()) % 7
        first_monday = jan_first if jan_first.weekday() == 0 else jan_first + timedelta(days=days_until_monday)
        return first_monday + timedelta(weeks=2)
    
    elif rule == 'memorial_day':
        may_end = date(year, 5, 31)
        return may_end - timedelta(days=may_end.weekday())
    
    elif rule == 'labor_day':
        sept_first = date(year, 9, 1)
        if sept_first.weekday() == 0:
            return sept_first
        days_until_monday = (7 - sept_first.weekday()) % 7
        return sept_first + timedelta(days=days_until_monday)
    
    return None


def is_theme_active(date_rule: dict, check_date: date) -> bool:
    """Check if a theme should be active on the given date."""
    rule_type = date_rule.get('type')
    
    if rule_type == 'fixed':
        try:
            start_str = date_rule.get('start', '')
            end_str = date_rule.get('end', '')
            if not start_str or not end_str:
                return False
            
            start_month, start_day = map(int, start_str.split('-'))
            end_month, end_day = map(int, end_str.split('-'))
            
            year = check_date.year
            start_date = date(year, start_month, start_day)
            end_date = date(year, end_month, end_day)
            
            if start_date > end_date:
                return check_date >= start_date or check_date <= end_date
            
            return start_date <= check_date <= end_date
        except:
            return False
    
    elif rule_type == 'dynamic':
        try:
            rule_name = date_rule.get('rule', '')
            offset_start = date_rule.get('offset_start', 0)
            offset_end = date_rule.get('offset_end', 0)
            
            base_date = calculate_dynamic_date(rule_name, check_date.year)
            if not base_date:
                return False
            
            start_date = base_date + timedelta(days=offset_start)
            end_date = base_date + timedelta(days=offset_end)
            
            return start_date <= check_date <= end_date
        except:
            return False
    
    return False


# ==========================================
# Logging
# ==========================================

def log(message: str, level: str = "INFO"):
    """Log with timestamp and level"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


# ==========================================
# Campaign Status Management
# ==========================================

def update_campaign_statuses() -> Dict[str, int]:
    """
    Update campaign statuses based on current time.
    
    State transitions:
    - scheduled -> active: when current time >= start_at
    - active -> ended: when current time >= end_at
    - paused campaigns are not auto-transitioned
    
    Returns:
        Dict with counts of activated and ended campaigns
    """
    now = datetime.now(timezone.utc)
    results = {"activated": 0, "ended": 0, "errors": 0}
    
    log("Checking campaign statuses...")
    
    # 1. Activate scheduled campaigns that have started
    try:
        scheduled = supabase.table('campaigns').select('id, name, start_at').eq(
            'status', 'scheduled'
        ).eq('is_active', True).execute()
        
        for campaign in (scheduled.data or []):
            try:
                start_at = datetime.fromisoformat(
                    campaign['start_at'].replace('Z', '+00:00')
                )
                
                if now >= start_at:
                    supabase.table('campaigns').update({
                        'status': 'active',
                        'updated_at': now.isoformat()
                    }).eq('id', campaign['id']).execute()
                    
                    log(f"✅ Activated campaign: {campaign['name']} (ID: {campaign['id']})")
                    results["activated"] += 1
                    
            except Exception as e:
                log(f"❌ Error activating campaign {campaign['id']}: {e}", "ERROR")
                results["errors"] += 1
                
    except Exception as e:
        log(f"❌ Error fetching scheduled campaigns: {e}", "ERROR")
        results["errors"] += 1
    
    # 2. End active campaigns that have passed end_at
    try:
        active = supabase.table('campaigns').select('id, name, end_at').eq(
            'status', 'active'
        ).execute()
        
        for campaign in (active.data or []):
            try:
                end_at = datetime.fromisoformat(
                    campaign['end_at'].replace('Z', '+00:00')
                )
                
                if now >= end_at:
                    supabase.table('campaigns').update({
                        'status': 'ended',
                        'is_active': False,
                        'updated_at': now.isoformat()
                    }).eq('id', campaign['id']).execute()
                    
                    log(f"🏁 Ended campaign: {campaign['name']} (ID: {campaign['id']})")
                    results["ended"] += 1
                    
            except Exception as e:
                log(f"❌ Error ending campaign {campaign['id']}: {e}", "ERROR")
                results["errors"] += 1
                
    except Exception as e:
        log(f"❌ Error fetching active campaigns: {e}", "ERROR")
        results["errors"] += 1
    
    return results


def get_upcoming_campaigns(hours: int = 24) -> List[Dict]:
    """
    Get campaigns starting within the next N hours.
    Useful for sending advance notifications.
    """
    now = datetime.now(timezone.utc)
    future = now + timedelta(hours=hours)
    
    try:
        result = supabase.table('campaigns').select('*').eq(
            'status', 'scheduled'
        ).gte('start_at', now.isoformat()).lte(
            'start_at', future.isoformat()
        ).execute()
        
        return result.data or []
    except Exception as e:
        log(f"❌ Error fetching upcoming campaigns: {e}", "ERROR")
        return []


# ==========================================
# Holiday Theme Status Logging
# ==========================================

def log_current_theme() -> Optional[Dict]:
    """
    Check and log the current active holiday theme.
    Useful for analytics and debugging.
    """
    today = date.today()
    
    try:
        result = supabase.table('holiday_themes').select('*').eq(
            'is_active', True
        ).order('priority', desc=True).execute()
        
        if not result.data:
            log("📅 No holiday themes configured")
            return None
        
        for theme in result.data:
            if is_theme_active(theme['date_rule'], today):
                log(f"🎉 Active holiday theme: {theme['name']} (ID: {theme['id']}, Priority: {theme['priority']})")
                
                # Log to analytics table (optional)
                try:
                    supabase.table('analytics_events').insert({
                        'event_type': 'holiday_theme_active',
                        'event_data': {
                            'theme_id': theme['id'],
                            'theme_name': theme['name'],
                            'date': today.isoformat()
                        },
                        'created_at': datetime.now(timezone.utc).isoformat()
                    }).execute()
                except:
                    pass  # Analytics logging is optional
                
                return theme
        
        log("📅 No active holiday theme for today")
        return None
        
    except Exception as e:
        log(f"❌ Error checking holiday theme: {e}", "ERROR")
        return None


def get_upcoming_themes(days: int = 7) -> List[Dict]:
    """
    Get themes that will be active within the next N days.
    Useful for preview and preparation.
    """
    today = date.today()
    
    try:
        result = supabase.table('holiday_themes').select('*').eq(
            'is_active', True
        ).order('priority', desc=True).execute()
        
        if not result.data:
            return []
        
        upcoming = []
        for day_offset in range(1, days + 1):
            check_date = today + timedelta(days=day_offset)
            for theme in result.data:
                if is_theme_active(theme['date_rule'], check_date):
                    if theme['id'] not in [t['id'] for t in upcoming]:
                        upcoming.append({
                            **theme,
                            'starts_in_days': day_offset
                        })
        
        return upcoming
        
    except Exception as e:
        log(f"❌ Error checking upcoming themes: {e}", "ERROR")
        return []


# ==========================================
# Summary Report
# ==========================================

def generate_summary_report() -> Dict[str, Any]:
    """Generate a summary report of campaigns and themes."""
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "campaigns": {
            "scheduled": 0,
            "active": 0,
            "paused": 0,
            "ended": 0,
            "total": 0
        },
        "themes": {
            "total": 0,
            "current": None,
            "upcoming": []
        }
    }
    
    # Count campaigns by status
    try:
        for status in ['scheduled', 'active', 'paused', 'ended']:
            result = supabase.table('campaigns').select('id', count='exact').eq(
                'status', status
            ).execute()
            report["campaigns"][status] = result.count or 0
        
        report["campaigns"]["total"] = sum([
            report["campaigns"]["scheduled"],
            report["campaigns"]["active"],
            report["campaigns"]["paused"],
            report["campaigns"]["ended"]
        ])
    except Exception as e:
        log(f"❌ Error counting campaigns: {e}", "ERROR")
    
    # Count themes
    try:
        result = supabase.table('holiday_themes').select('id', count='exact').eq(
            'is_active', True
        ).execute()
        report["themes"]["total"] = result.count or 0
    except:
        pass
    
    # Get current theme
    try:
        result = supabase.table('holiday_themes').select('*').eq(
            'is_active', True
        ).order('priority', desc=True).execute()
        
        today = date.today()
        for theme in (result.data or []):
            if is_theme_active(theme['date_rule'], today):
                report["themes"]["current"] = theme['name']
                break
    except:
        pass
    
    # Get upcoming themes
    upcoming = get_upcoming_themes(7)
    report["themes"]["upcoming"] = [
        {"name": t['name'], "in_days": t['starts_in_days']} 
        for t in upcoming[:3]
    ]
    
    return report


# ==========================================
# Main Entry Point
# ==========================================

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
